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
    connection.execute('''INSERT INTO ai_executions(id,user_id,request_id,body_hash,task_type,model_version,system_prompt_version,
        prompt_version,policy_version,profile_version,input_evidence,context_snapshot,structured_result,validation_status,failure_code,latency_ms,usage,created_at,retained_until)
        VALUES(%s,%s,%s,%s,'walking_estimate',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',values)


def insert_path(connection,values):
    connection.execute('''INSERT INTO walking_paths(id,user_id,path_key,candidate_id,origin_ref,destination_ref,direction,scope,
        place_refs,evidence,verified_at,calculated_at,expires_at,retained_until) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)''',values)


def insert_estimate(connection,values):
    connection.execute('INSERT INTO walking_estimates VALUES(%s,%s,%s,%s,%s)',values)


def insert_revision(connection,values):
    connection.execute('''INSERT INTO walking_estimate_revisions(id,user_id,estimate_id,revision_no,ai_execution_id,profile_version,
        base_seconds,applied_duration_factor,estimated_seconds,method,source,calculated_at,expires_at,retained_until)
        VALUES(%s,%s,%s,1,%s,%s,%s,%s,%s,%s,'ai_estimate',%s,%s,%s)''',values)


def execution_estimates(connection,user_id,execution_id):
    return connection.execute('''SELECT p.candidate_id,r.estimate_id,r.id AS revision_id,r.expires_at FROM walking_estimate_revisions r
        JOIN walking_estimates e ON (e.id,e.user_id)=(r.estimate_id,r.user_id)
        JOIN walking_paths p ON (p.id,p.user_id)=(e.walking_path_id,e.user_id)
        WHERE r.user_id=%s AND r.ai_execution_id=%s ORDER BY p.candidate_id''',(user_id,execution_id)).fetchall()


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
