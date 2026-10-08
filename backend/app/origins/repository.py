"""SQL for reading owned places during origin validation."""


def find_owned_place(connection, user_id, place_id):
    return connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                              (place_id, user_id)).fetchone()
