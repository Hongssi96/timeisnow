"""Read the owned search without extending its retention or cleaning other jobs."""


def find_search(connection, search_id, user_id):
    return connection.execute('SELECT * FROM journey_searches WHERE id=%s AND user_id=%s',
                              (search_id, user_id)).fetchone()
