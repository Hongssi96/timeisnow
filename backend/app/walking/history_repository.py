"""All SQL for immutable walking history and owned summary reads."""

def lock(connection,user_id):
    connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',('routine-write:'+str(user_id),))


def profile(connection,user_id):
    return connection.execute("SELECT p.*,u.status FROM user_profiles p JOIN users u ON u.id=p.user_id WHERE p.user_id=%s FOR SHARE OF p,u",(user_id,)).fetchone()


def clock(connection):
    return connection.execute('SELECT clock_timestamp() AS now').fetchone()['now']


def execution(connection,user_id,request_id):
    return connection.execute('SELECT * FROM ai_executions WHERE user_id=%s AND request_id=%s',(user_id,request_id)).fetchone()


def insert_execution(connection,values):
    connection.execute("""INSERT INTO ai_executions(id,user_id,request_id,body_hash,task_type,model_version,system_prompt_version,
        prompt_version,policy_version,profile_version,input_evidence,context_snapshot,structured_result,validation_status,failure_code,latency_ms,usage,created_at,retained_until,reused_estimates)
        VALUES(%s,%s,%s,%s,'walking_estimate',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",values)


def insert_path(connection,values):
    connection.execute('''INSERT INTO walking_paths(id,user_id,path_key,candidate_id,origin_ref,destination_ref,direction,scope,
        place_refs,evidence,verified_at,calculated_at,expires_at,retained_until,cache_key,cache_identity) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',values)


def insert_estimate(connection,values):
    connection.execute('INSERT INTO walking_estimates VALUES(%s,%s,%s,%s,%s)',values)


def insert_revision(connection,values):
    connection.execute('''INSERT INTO walking_estimate_revisions(id,user_id,estimate_id,revision_no,ai_execution_id,profile_version,
        base_seconds,applied_duration_factor,estimated_seconds,method,source,calculated_at,expires_at,retained_until)
        VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,%s,'ai_estimate',%s,%s,%s)''',values)


def execution_estimates(connection,user_id,execution_id):
    return connection.execute("""SELECT COALESCE(r.candidate_id,p.candidate_id) AS candidate_id,r.estimate_id,r.id AS revision_id,r.expires_at,false AS reused,r.source FROM walking_estimate_revisions r
        JOIN walking_estimates e ON (e.id,e.user_id)=(r.estimate_id,r.user_id)
        JOIN walking_paths p ON (p.id,p.user_id)=(e.walking_path_id,e.user_id)
        WHERE r.user_id=%s AND r.ai_execution_id=%s
        UNION ALL
        SELECT link->>'candidate_id',r.estimate_id,r.id,LEAST(r.expires_at,(link->>'expires_at')::timestamptz),true,r.source
        FROM ai_executions a CROSS JOIN LATERAL jsonb_array_elements(a.reused_estimates) link
        JOIN walking_estimate_revisions r ON r.id=(link->>'revision_id')::uuid AND r.user_id=a.user_id
        JOIN walking_estimates e ON (e.id,e.user_id)=(r.estimate_id,r.user_id) AND e.id=(link->>'estimate_id')::uuid
        JOIN walking_paths p ON (p.id,p.user_id)=(e.walking_path_id,e.user_id)
        WHERE a.user_id=%s AND a.id=%s AND p.retained_until>clock_timestamp() AND r.retained_until>clock_timestamp()
        ORDER BY candidate_id""",(user_id,execution_id,user_id,execution_id)).fetchall()


def cache_candidate(connection,user_id,cache_key,revision_id=None):
    return connection.execute("""SELECT r.*,p.cache_key,p.cache_identity,p.place_refs,p.expires_at AS path_expires_at,
        p.retained_until AS path_retained_until,a.input_evidence,a.model_version,a.system_prompt_version,a.prompt_version,
        a.policy_version,a.retained_until AS execution_retained_until,a.validation_status,original.model_version AS baseline_model_version
        FROM walking_paths p JOIN walking_estimates e ON (e.walking_path_id,e.user_id)=(p.id,p.user_id)
        JOIN walking_estimate_revisions r ON (r.estimate_id,r.user_id)=(e.id,e.user_id)
        JOIN ai_executions a ON (a.id,a.user_id)=(r.ai_execution_id,r.user_id)
        JOIN walking_estimate_revisions baseline ON (baseline.estimate_id,baseline.user_id)=(e.id,e.user_id) AND baseline.revision_no=1
        JOIN ai_executions original ON (original.id,original.user_id)=(baseline.ai_execution_id,baseline.user_id)
        WHERE original.retained_until>clock_timestamp() AND p.user_id=%s AND p.cache_key=%s AND (%s::uuid IS NULL OR r.id=%s::uuid)
        AND p.expires_at>clock_timestamp() AND r.expires_at>clock_timestamp()
        AND p.retained_until>clock_timestamp() AND r.retained_until>clock_timestamp() AND a.retained_until>clock_timestamp()
        AND a.validation_status='validated'
        ORDER BY r.calculated_at DESC,r.id DESC LIMIT 1""",(user_id,cache_key,revision_id,revision_id)).fetchone()


def summary(connection,user_id,estimate_id):
    return connection.execute('''SELECT r.*,p.scope,p.place_refs,p.retained_until AS path_retained_until,
        e.policy_version,a.prompt_version FROM walking_estimates e
        JOIN walking_paths p ON (p.id,p.user_id)=(e.walking_path_id,e.user_id)
        JOIN walking_estimate_revisions r ON (r.estimate_id,r.user_id)=(e.id,e.user_id)
        JOIN ai_executions a ON (a.id,a.user_id)=(r.ai_execution_id,r.user_id)
        WHERE e.user_id=%s AND e.id=%s ORDER BY r.revision_no DESC LIMIT 1''',(user_id,estimate_id)).fetchone()


def purge(connection,user_id):
    connection.execute('DELETE FROM walking_paths WHERE user_id=%s AND retained_until<=clock_timestamp()',(user_id,))
    connection.execute('DELETE FROM ai_executions WHERE user_id=%s AND retained_until<=clock_timestamp()',(user_id,))


def try_execution_lock(connection,key):
    return connection.execute('SELECT pg_try_advisory_lock(hashtextextended(%s,0)) AS acquired',(key,)).fetchone()['acquired']


def release_execution_lock(connection,key):
    connection.execute('SELECT pg_advisory_unlock(hashtextextended(%s,0))',(key,))


def insert_recalculation(connection,values):
    connection.execute("""INSERT INTO walking_estimate_revisions(id,user_id,estimate_id,revision_no,ai_execution_id,profile_version,
        base_seconds,applied_duration_factor,estimated_seconds,method,source,calculated_at,expires_at,retained_until,parent_revision_id,candidate_id)
        SELECT %s,%s,%s,COALESCE(MAX(revision_no),0)+1,%s,%s,%s,%s,%s,%s,'profile_recalculation',%s,%s,%s,%s,%s
        FROM walking_estimate_revisions WHERE user_id=%s AND estimate_id=%s""",values)
