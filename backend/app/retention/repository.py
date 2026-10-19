"""Owner-scoped expiry queries; all destructive work shares trip/routine locks."""
OBS_EXPIRED="""(o.expires_at<=clock_timestamp() OR NOT EXISTS(
  SELECT 1 FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
  WHERE t.id=o.trip_id AND t.user_id=o.user_id AND t.expires_at>clock_timestamp() AND g.expires_at>clock_timestamp())
  OR (o.path_key IS NOT NULL AND NOT EXISTS(SELECT 1 FROM walking_paths p
    WHERE p.user_id=o.user_id AND p.cache_key=o.path_key AND p.retained_until>clock_timestamp())))"""

def pending(c,owner):
    queries=[]
    for table,expiry in [('guidance_snapshots','expires_at'),('manual_trips','expires_at'),
      ('walking_paths','retained_until'),('walking_estimate_revisions','retained_until'),('ai_executions','retained_until'),
      ('manual_trip_creation_keys','expires_at'),('trip_record_mutations','expires_at'),('trip_exports','expires_at'),('walking_segment_measurements','expires_at')]:
        queries.append(f'SELECT 1 FROM {table} WHERE user_id=%s AND {expiry}<=clock_timestamp()')
    queries.append('SELECT 1 FROM walking_learning_observations o WHERE o.user_id=%s AND '+OBS_EXPIRED)
    queries.append('''SELECT 1 FROM trip_record_mutations m WHERE m.user_id=%s AND m.kind<>'delete'
      AND NOT EXISTS(SELECT 1 FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
        WHERE t.user_id=m.user_id AND t.id=m.trip_id AND t.expires_at>clock_timestamp() AND g.expires_at>clock_timestamp())''')
    queries.append('''SELECT 1 FROM walking_segment_selections s WHERE s.user_id=%s AND NOT EXISTS(
      SELECT 1 FROM walking_segment_measurements m WHERE m.user_id=s.user_id AND m.context_key=s.context_key AND m.expires_at>clock_timestamp())''')
    queries.append('''SELECT 1 FROM walking_learning_updates u WHERE u.user_id=%s AND EXISTS(
        SELECT 1 FROM jsonb_array_elements_text(u.sample_ids) s WHERE NOT EXISTS(
          SELECT 1 FROM walking_learning_observations o WHERE o.user_id=u.user_id AND o.id::text=s))''')
    return c.execute('SELECT EXISTS('+' UNION ALL '.join(queries)+') AS pending',(owner,)*len(queries)).fetchone()['pending']

def remove(c,owner):
    observations=c.execute('DELETE FROM walking_learning_observations o WHERE o.user_id=%s AND '+OBS_EXPIRED+' RETURNING status',(owner,)).fetchall()
    c.execute('''DELETE FROM trip_record_mutations m WHERE m.user_id=%s AND (m.expires_at<=clock_timestamp()
      OR (m.kind<>'delete' AND NOT EXISTS(SELECT 1 FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
        WHERE t.id=m.trip_id AND t.user_id=m.user_id AND t.expires_at>clock_timestamp() AND g.expires_at>clock_timestamp())))''',(owner,))
    c.execute('''DELETE FROM manual_trip_creation_keys k WHERE k.user_id=%s AND (k.expires_at<=clock_timestamp()
      OR (k.trip_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM manual_trips t JOIN guidance_snapshots g ON g.id=t.guidance_id
        WHERE t.id=k.trip_id AND t.user_id=k.user_id AND t.expires_at>clock_timestamp() AND g.expires_at>clock_timestamp())))''',(owner,))
    trips=c.execute('''DELETE FROM guidance_snapshots g WHERE g.user_id=%s AND (g.expires_at<=clock_timestamp()
      OR EXISTS(SELECT 1 FROM manual_trips t WHERE t.guidance_id=g.id AND t.user_id=g.user_id AND t.expires_at<=clock_timestamp()))''',(owner,)).rowcount
    references=c.execute('''UPDATE walking_learning_updates u SET sample_ids=COALESCE((SELECT jsonb_agg(s) FROM jsonb_array_elements(u.sample_ids) s
      WHERE EXISTS(SELECT 1 FROM walking_learning_observations o WHERE o.user_id=u.user_id AND o.id::text=s#>>'{}')),'[]')
      WHERE u.user_id=%s AND EXISTS(SELECT 1 FROM jsonb_array_elements_text(u.sample_ids) s
        WHERE NOT EXISTS(SELECT 1 FROM walking_learning_observations o WHERE o.user_id=u.user_id AND o.id::text=s))''',(owner,)).rowcount
    c.execute('DELETE FROM walking_estimate_revisions WHERE user_id=%s AND retained_until<=clock_timestamp()',(owner,))
    from app.walking.history_repository import purge
    purge(c,owner)
    c.execute('DELETE FROM trip_exports WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))
    from app.personalization.segments_repository import clean
    clean(c,owner)
    return {'observations':len(observations),'trips':trips,'rebuild':bool(references or any(o['status']=='valid' for o in observations))}

def owners(c,after=None):
    return c.execute('SELECT user_id FROM user_profiles WHERE (%s::uuid IS NULL OR user_id>%s) ORDER BY user_id LIMIT 100',(after,after)).fetchall()

def timeouts(c):
    c.execute("SET LOCAL lock_timeout='5s'");c.execute("SET LOCAL statement_timeout='30s'")
