from typing import List, Set, Tuple, Optional, Any
import re

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _fetchone_value(cursor, query: str, params: Tuple[Any, ...]) -> Optional[Any]:
    cursor.execute(query, params)
    row = cursor.fetchone()
    return None if row is None else row[0]


def _get_or_create_artist(cursor, artist_name: str) -> int:
    artist_id = _fetchone_value(
        cursor,
        "SELECT artist_id FROM artists WHERE artist_name = %s",
        (artist_name,),
    )
    if artist_id is not None:
        return artist_id
    cursor.execute("INSERT INTO artists (artist_name) VALUES (%s)", (artist_name,))
    return cursor.lastrowid


def _get_or_create_genre(cursor, genre_name: str) -> int:
    genre_id = _fetchone_value(
        cursor,
        "SELECT genre_id FROM genres WHERE genre_name = %s",
        (genre_name,),
    )
    if genre_id is not None:
        return genre_id
    cursor.execute("INSERT INTO genres (genre_name) VALUES (%s)", (genre_name,))
    return cursor.lastrowid


def _get_song_id(cursor, artist_name: str, title: str) -> Optional[int]:
    return _fetchone_value(
        cursor,
        """
        SELECT s.song_id
        FROM songs s
        JOIN artists a ON a.artist_id = s.artist_id
        WHERE a.artist_name = %s AND s.title = %s
        """,
        (artist_name, title),
    )


def _effective_release_date_sql() -> str:
    return "COALESCE(s.release_date, al.release_date)"


def clear_database(mydb):
    """Remove all rows from every table while preserving the schema."""
    cursor = mydb.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ("ratings", "song_genres", "songs", "albums", "genres", "users", "artists"):
        cursor.execute(f"TRUNCATE TABLE {table}")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    mydb.commit()
    cursor.close()


def load_single_songs(mydb, single_songs: List[Tuple[str, Tuple[str, ...], str, str]]) -> Set[Tuple[str, str]]:
    """
    Insert singles.

    Input tuple format: (song_title, genres, artist_name, release_date).
    Returns (song_title, artist_name) for rejected rows.
    A single is rejected when the artist already has a song with that title,
    when it has no genre, or when an insert violates a database constraint.
    """
    cursor = mydb.cursor()
    rejects: Set[Tuple[str, str]] = set()

    for title, genres, artist_name, release_date in single_songs:
        if not title or not artist_name or not release_date or not genres:
            rejects.add((title, artist_name))
            continue

        try:
            artist_id = _get_or_create_artist(cursor, artist_name)
            if _fetchone_value(cursor, "SELECT song_id FROM songs WHERE title = %s AND artist_id = %s", (title, artist_id)) is not None:
                rejects.add((title, artist_name))
                continue

            cursor.execute(
                """
                INSERT INTO songs (title, artist_id, album_id, release_date)
                VALUES (%s, %s, NULL, %s)
                """,
                (title, artist_id, release_date),
            )
            song_id = cursor.lastrowid

            for genre_name in genres:
                if not genre_name:
                    continue
                genre_id = _get_or_create_genre(cursor, genre_name)
                cursor.execute(
                    "INSERT IGNORE INTO song_genres (song_id, genre_id) VALUES (%s, %s)",
                    (song_id, genre_id),
                )

            cursor.execute("SELECT COUNT(*) FROM song_genres WHERE song_id = %s", (song_id,))
            if cursor.fetchone()[0] == 0:
                cursor.execute("DELETE FROM songs WHERE song_id = %s", (song_id,))
                rejects.add((title, artist_name))
        except Exception:
            mydb.rollback()
            rejects.add((title, artist_name))
            cursor = mydb.cursor()

    mydb.commit()
    cursor.close()
    return rejects


def _parse_album_tuple(album: Tuple[Any, ...]):
    """Accept the common 5-field format and a defensively supported 4-field format."""
    if len(album) == 5:
        album_name = album[0]
        songs = album[4]
        middle = list(album[1:4])
        date_index = next((i for i, value in enumerate(middle) if isinstance(value, str) and _DATE_RE.match(value)), None)
        if date_index is None:
            genre, artist_name, release_date = middle[0], middle[1], middle[2]
        else:
            release_date = middle.pop(date_index)
            genre, artist_name = middle[0], middle[1]
        return album_name, genre, artist_name, release_date, songs
        
    if len(album) == 4:
        album_name = album[0]
        songs = album[3]
        middle = list(album[1:3])
        
        # Safely locate the release date using the regex
        date_index = next((i for i, value in enumerate(middle) if isinstance(value, str) and _DATE_RE.match(value)), None)
        
        if date_index is not None:
            release_date = middle.pop(date_index)
            artist_name = middle[0]
        else:
            # Absolute fallback if regex fails
            artist_name, release_date = middle[0], middle[1]
            
        return album_name, "Unknown", artist_name, release_date, songs
        
    raise ValueError("Album tuple must have 4 or 5 fields")


def load_albums(mydb, albums: List[Tuple]) -> Set[Tuple[str, str]]:
    """
    Insert albums and their songs.

    Supported input format: (album_name, genre, artist_name, release_date, songs).
    Returns (album_name, artist_name) for rejected albums.
    An album is rejected if the same artist already has that album name, if any
    listed song title was already recorded by that artist, or if the album has no songs.
    """
    cursor = mydb.cursor()
    rejects: Set[Tuple[str, str]] = set()

    for album in albums:
        try:
            album_name, genre_name, artist_name, release_date, songs = _parse_album_tuple(album)
            if not album_name or not genre_name or not artist_name or not release_date or not songs:
                rejects.add((album_name, artist_name))
                continue

            artist_id = _get_or_create_artist(cursor, artist_name)
            if _fetchone_value(cursor, "SELECT album_id FROM albums WHERE album_name = %s AND artist_id = %s", (album_name, artist_id)) is not None:
                rejects.add((album_name, artist_name))
                continue

            duplicate_song = False
            for title in songs:
                if not title or _fetchone_value(cursor, "SELECT song_id FROM songs WHERE title = %s AND artist_id = %s", (title, artist_id)) is not None:
                    duplicate_song = True
                    break
            if duplicate_song:
                rejects.add((album_name, artist_name))
                continue

            genre_id = _get_or_create_genre(cursor, genre_name)
            cursor.execute(
                """
                INSERT INTO albums (album_name, artist_id, release_date, genre_id)
                VALUES (%s, %s, %s, %s)
                """,
                (album_name, artist_id, release_date, genre_id),
            )
            album_id = cursor.lastrowid

           # Removed the INSERT INTO song_genres block!
                song_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO song_genres (song_id, genre_id) VALUES (%s, %s)",
                    (song_id, genre_id),
                )
        except Exception:
            mydb.rollback()
            try:
                album_name = album[0]
                artist_name = album[2] if len(album) >= 3 else ""
            except Exception:
                album_name, artist_name = "", ""
            rejects.add((album_name, artist_name))
            cursor = mydb.cursor()

    mydb.commit()
    cursor.close()
    return rejects


def load_users(mydb, users: List[str]) -> Set[str]:
    """Insert users. Return usernames that were rejected because they already existed or were invalid."""
    cursor = mydb.cursor()
    rejects: Set[str] = set()
    for username in users:
        if not username:
            rejects.add(username)
            continue
        try:
            cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
        except Exception:
            rejects.add(username)
    mydb.commit()
    cursor.close()
    return rejects


def load_song_ratings(mydb, song_ratings: List[Tuple[str, Tuple[str, str], int, str]]) -> Set[Tuple[str, str, str]]:
    """
    Insert song ratings.

    Input tuple format: (username, (artist_name, song_title), rating, rating_date).
    Returns (username, artist_name, song_title) for rejected ratings.
    """
    cursor = mydb.cursor()
    rejects: Set[Tuple[str, str, str]] = set()

    for username, song_info, rating, rating_date in song_ratings:
        artist_name, title = song_info
        reject_key = (username, artist_name, title)
        try:
            if rating not in (1, 2, 3, 4, 5):
                rejects.add(reject_key)
                continue
            if _fetchone_value(cursor, "SELECT username FROM users WHERE username = %s", (username,)) is None:
                rejects.add(reject_key)
                continue
            song_id = _get_song_id(cursor, artist_name, title)
            if song_id is None:
                rejects.add(reject_key)
                continue
            if _fetchone_value(cursor, "SELECT song_id FROM ratings WHERE username = %s AND song_id = %s", (username, song_id)) is not None:
                rejects.add(reject_key)
                continue

            cursor.execute(
                """
                INSERT INTO ratings (username, song_id, score, rating_date)
                VALUES (%s, %s, %s, %s)
                """,
                (username, song_id, rating, rating_date),
            )
        except Exception:
            mydb.rollback()
            rejects.add(reject_key)
            cursor = mydb.cursor()

    mydb.commit()
    cursor.close()
    return rejects


def get_most_prolific_individual_artists(mydb, n: int, year_range: Tuple[int, int]) -> List[Tuple[str, int]]:
    """Return the n artists with the most released songs in the inclusive year range."""
    cursor = mydb.cursor()
    cursor.execute(
        f"""
        SELECT a.artist_name, COUNT(*) AS song_count
        FROM artists a
        JOIN songs s ON s.artist_id = a.artist_id
        LEFT JOIN albums al ON al.album_id = s.album_id
        WHERE YEAR({_effective_release_date_sql()}) BETWEEN %s AND %s
        GROUP BY a.artist_id, a.artist_name
        ORDER BY song_count DESC, a.artist_name ASC
        LIMIT %s
        """,
        (year_range[0], year_range[1], n),
    )
    result = [(row[0], int(row[1])) for row in cursor.fetchall()]
    cursor.close()
    return result


def get_artists_last_single_in_year(mydb, year: int) -> Set[str]:
    """Return artists whose most recent single was released in the given year."""
    cursor = mydb.cursor()
    cursor.execute(
        """
        SELECT a.artist_name
        FROM artists a
        JOIN songs s ON s.artist_id = a.artist_id
        WHERE s.album_id IS NULL
        GROUP BY a.artist_id, a.artist_name
        HAVING YEAR(MAX(s.release_date)) = %s
        """,
        (year,),
    )
    result = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return result


def get_top_song_genres(mydb, n: int) -> List[Tuple[str, int]]:
    """Return the n genres assigned to the most songs."""
    cursor = mydb.cursor()
    cursor.execute(
        """
        SELECT g.genre_name, COUNT(*) AS song_count
        FROM genres g
        JOIN (
            -- Singles: Get genre from song_genres
            SELECT sg.song_id, sg.genre_id
            FROM song_genres sg
            UNION ALL
            -- Album Tracks: Get genre from the albums table
            SELECT s.song_id, al.genre_id
            FROM songs s
            JOIN albums al ON s.album_id = al.album_id
            WHERE s.album_id IS NOT NULL
        ) AS all_song_genres ON g.genre_id = all_song_genres.genre_id
        GROUP BY g.genre_id, g.genre_name
        ORDER BY song_count DESC, g.genre_name ASC
        LIMIT %s
        """,
        (n,),
    )
    result = [(row[0], int(row[1])) for row in cursor.fetchall()]
    cursor.close()
    return result


def get_album_and_single_artists(mydb) -> Set[str]:
    """Return artists that have at least one album song and at least one single."""
    cursor = mydb.cursor()
    cursor.execute(
        """
        SELECT DISTINCT a.artist_name
        FROM artists a
        WHERE EXISTS (
            SELECT 1 FROM songs s1
            WHERE s1.artist_id = a.artist_id AND s1.album_id IS NULL
        )
        AND EXISTS (
            SELECT 1 FROM songs s2
            WHERE s2.artist_id = a.artist_id AND s2.album_id IS NOT NULL
        )
        """
    )
    result = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return result


def get_most_rated_songs(mydb, year_range: Tuple[int, int], n: int) -> List[Tuple[str, str, int]]:
    """Return the n songs receiving the most ratings in the inclusive rating-date year range."""
    cursor = mydb.cursor()
    cursor.execute(
        """
        SELECT s.title, a.artist_name, COUNT(*) AS rating_count
        FROM ratings r
        JOIN songs s ON s.song_id = r.song_id
        JOIN artists a ON a.artist_id = s.artist_id
        WHERE YEAR(r.rating_date) BETWEEN %s AND %s
        GROUP BY s.song_id, s.title, a.artist_name
        ORDER BY rating_count DESC, s.title ASC, a.artist_name ASC
        LIMIT %s
        """,
        (year_range[0], year_range[1], n),
    )
    result = [(row[0], row[1], int(row[2])) for row in cursor.fetchall()]
    cursor.close()
    return result


def get_most_engaged_users(mydb, year_range: Tuple[int, int], n: int) -> List[Tuple[str, int]]:
    """Return the n users with the most ratings in the inclusive rating-date year range."""
    cursor = mydb.cursor()
    cursor.execute(
        """
        SELECT username, COUNT(*) AS rating_count
        FROM ratings
        WHERE YEAR(rating_date) BETWEEN %s AND %s
        GROUP BY username
        ORDER BY rating_count DESC, username ASC
        LIMIT %s
        """,
        (year_range[0], year_range[1], n),
    )
    result = [(row[0], int(row[1])) for row in cursor.fetchall()]
    cursor.close()
    return result
