"""Bounded export queries; callers share the manual-trip owner lock."""
def clean(c,owner):
    c.execute('DELETE FROM trip_exports WHERE user_id=%s AND expires_at<=clock_timestamp()',(owner,))

def create(c,owner,identifier,start,end):
    return c.execute('''INSERT INTO trip_exports(id,user_id,range_from,range_to)
      VALUES(%s,%s,%s,%s) RETURNING *''',(identifier,owner,start,end)).fetchone()

def owned(c,owner,identifier):
    return c.execute('SELECT * FROM trip_exports WHERE id=%s AND user_id=%s AND expires_at>clock_timestamp()',
      (identifier,owner)).fetchone()

def rows(c,owner,start,end,cutoff):
    return c.execute('''SELECT t.* FROM manual_trips t
      WHERE user_id=%s AND created_at>=%s AND created_at<%s AND created_at<=%s
      AND expires_at>clock_timestamp() ORDER BY created_at,id LIMIT 501''',(owner,start,end,cutoff)).fetchall()

def corrections(c,tid):
    return c.execute('''SELECT a.* FROM trip_event_corrections a JOIN manual_trip_events e ON e.id=a.event_id
      WHERE e.trip_id=%s ORDER BY a.created_at,a.id''',(tid,)).fetchall()

def observation(c,owner,tid):
    return c.execute('''SELECT response,version,confirmation FROM walking_learning_observations
      WHERE user_id=%s AND trip_id=%s AND expires_at>clock_timestamp()''',(owner,tid)).fetchone()
