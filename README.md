# Music Streaming Relational Database & Analytics Engine

A MySQL relational database and Python analytics module designed to manage and query a music catalog (artists, albums, songs, genres, users, and ratings).

## Project Overview

* **Normalized Schema Design**: Built in 3NF to minimize data redundancy using surrogate keys, composite uniqueness constraints, and foreign key relationships.
* **ETL Ingestion Pipeline**: Transaction-safe Python script (`music_db.py`) to parse, load, and validate incoming catalog data while handling constraints and rejections.
* **Complex SQL Analytics**: Implements analytical query functions using multi-table joins, derived tables, `UNION ALL`, subqueries with `EXISTS`, and aggregation.

## File Structure

* `music_db.sql`: Database definition script with table schemas, primary/foreign keys, check constraints, and indexes.
* `music_db.py`: Python driver script containing database clearing logic, data loaders, and analytical query functions.
* `music_db.pdf`: Relational schema diagram mapping entities, primary keys (PK), foreign keys (FK), and cardinality.

## Data Model Highlights

* **Artists & Albums**: Artists are uniquely identified by name. Album names are unique per artist (`UNIQUE(album_name, artist_id)`).
* **Flexible Track Releases**: Accommodates both singles and album tracks. Album tracks inherit the album's release date, while singles maintain individual release dates.
* **Multi-Genre Support**: Many-to-many junction table (`song_genres`) connects songs to pre-defined genres.
* **Ratings & Engagement**: Stores user ratings restricted to integer scores between 1 and 5 (`CHECK (score BETWEEN 1 AND 5)`).

## Included Analytics Queries

The `music_db.py` module includes pre-built functions for platform metrics:
* `get_most_prolific_individual_artists(mydb, n, year_range)`: Ranks top $N$ artists by song releases in a year window.
* `get_artists_last_single_in_year(mydb, year)`: Discovers artists whose final single was released in a target year.
* `get_top_song_genres(mydb, n)`: Ranks the top $N$ genres across both single and album tracks.
* `get_album_and_single_artists(mydb)`: Discovers crossover artists with both album tracks and singles.
* `get_most_rated_songs(mydb, year_range, n)`: Finds top $N$ most-rated songs over a date range.
* `get_most_engaged_users(mydb, year_range, n)`: Finds top $N$ most active users by rating volume.

## Quickstart

### 1. Import Schema
```bash
mysql -u root -p < music_db.sql

**Execution Example**

import mysql.connector
import music_db

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_password",
    database="music_db"
)

# Fetch top 5 genres across all tracks
top_genres = music_db.get_top_song_genres(mydb, n=5)
print(top_genres)
