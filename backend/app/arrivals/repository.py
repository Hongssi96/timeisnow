def search(connection,user_id,search_id):
    return connection.execute("SELECT s.* FROM journey_searches s JOIN users u ON u.id=s.user_id WHERE s.user_id=%s AND s.id=%s AND u.status='active'",(user_id,search_id)).fetchone()
