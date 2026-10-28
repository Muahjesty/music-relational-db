SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS ratings;
DROP TABLE IF EXISTS song_genres;
DROP TABLE IF EXISTS songs;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS genres;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS artists;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE artists (
    artist_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    artist_name VARCHAR(255) NOT NULL,
    UNIQUE KEY uq_artists_artist_name (artist_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE genres (
    genre_id SMALLINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL,
    UNIQUE KEY uq_genres_genre_name (genre_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE albums (
    album_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    album_name VARCHAR(255) NOT NULL,
    artist_id BIGINT UNSIGNED NOT NULL,
    release_date DATE NOT NULL,
    genre_id SMALLINT UNSIGNED NOT NULL,
    UNIQUE KEY uq_albums_album_artist (album_name, artist_id),
    KEY idx_albums_artist_id (artist_id),
    KEY idx_albums_genre_id (genre_id),
    CONSTRAINT fk_albums_artist FOREIGN KEY (artist_id) REFERENCES artists (artist_id) ON DELETE CASCADE,
    CONSTRAINT fk_albums_genre FOREIGN KEY (genre_id) REFERENCES genres (genre_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE songs (
    song_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    artist_id BIGINT UNSIGNED NOT NULL,
    album_id BIGINT UNSIGNED NULL,
    release_date DATE NULL,
    UNIQUE KEY uq_songs_title_artist (title, artist_id),
    KEY idx_songs_artist_id (artist_id),
    KEY idx_songs_album_id (album_id),
    KEY idx_songs_release_date (release_date),
    CONSTRAINT fk_songs_artist FOREIGN KEY (artist_id) REFERENCES artists (artist_id) ON DELETE CASCADE,
    CONSTRAINT fk_songs_album FOREIGN KEY (album_id) REFERENCES albums (album_id) ON DELETE CASCADE,
    CONSTRAINT chk_song_date_source CHECK ((album_id IS NULL AND release_date IS NOT NULL) OR (album_id IS NOT NULL AND release_date IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE song_genres (
    song_id BIGINT UNSIGNED NOT NULL,
    genre_id SMALLINT UNSIGNED NOT NULL,
    PRIMARY KEY (song_id, genre_id),
    KEY idx_song_genres_genre_id (genre_id),
    CONSTRAINT fk_song_genres_song FOREIGN KEY (song_id) REFERENCES songs (song_id) ON DELETE CASCADE,
    CONSTRAINT fk_song_genres_genre FOREIGN KEY (genre_id) REFERENCES genres (genre_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE users (
    username VARCHAR(255) NOT NULL PRIMARY KEY
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE ratings (
    username VARCHAR(255) NOT NULL,
    song_id BIGINT UNSIGNED NOT NULL,
    score TINYINT UNSIGNED NOT NULL,
    rating_date DATE NOT NULL,
    PRIMARY KEY (username, song_id),
    KEY idx_ratings_song_id (song_id),
    KEY idx_ratings_rating_date (rating_date),
    CONSTRAINT fk_ratings_user FOREIGN KEY (username) REFERENCES users (username) ON DELETE CASCADE,
    CONSTRAINT fk_ratings_song FOREIGN KEY (song_id) REFERENCES songs (song_id) ON DELETE CASCADE,
    CONSTRAINT chk_ratings_score CHECK (score BETWEEN 1 AND 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
