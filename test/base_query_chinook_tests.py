from breezeblocks import Table
from breezeblocks.exceptions import QueryError
from breezeblocks.sql.aggregates import Count_, RecordCount
from breezeblocks.sql.join import InnerJoin, FullJoin, LeftJoin, RightJoin, CrossJoin
from breezeblocks.sql.operators import Equal_, In_
from breezeblocks.sql import Value


class BaseQueryChinookTests(object):
    """Tests with the Chinook Database"""
    
    tables = {
        "Artist": Table("Artist", ["ArtistId", "Name"]),
        "Genre": Table("Genre", ["GenreId", "Name"]),
        "Album": Table("Album", ["AlbumId", "Title", "ArtistId"]),
        "Track": Table("Track",
            ["TrackId", "Name", "AlbumId", "MediaTypeId", "GenreId", "Composer", "Milliseconds", "Bytes", "UnitPrice"]),
        "Playlist": Table("Playlist", ["PlaylistId", "Name"]),
        "PlaylistTrack": Table("PlaylistTrack", ["PlaylistId", "TrackId"])
    }
    
    def test_tableQuery(self):
        """Tests a simple select on a table."""
        q = self.db.query(self.tables["Artist"]).get()
        
        # Assertion checks that all columns in the table are present in
        # each row returned.
        for row in q.execute():
            self.assertTrue(hasattr(row, "ArtistId"))
            self.assertTrue(hasattr(row, "Name"))
    
    def test_columnQuery(self):
        """Tests a simple select on a column."""
        q = self.db.query(self.tables["Artist"].columns["Name"]).get()
        
        # Assertion checks that only the queried columns are returned.
        for row in q.execute():
            self.assertTrue(hasattr(row, "Name"))
            self.assertFalse(hasattr(row, "ArtistId"))
    
    def test_simpleWhereClause(self):
        """Tests a simple where clause."""
        tbl_genre = self.tables["Genre"]
        tbl_track = self.tables["Track"]
        genre_id = self.db.query(tbl_genre)\
            .where(tbl_genre.columns["Name"] == "Alternative & Punk")\
            .get().execute()[0].GenreId
        
        q = self.db.query(tbl_track.columns["GenreId"])\
            .where(tbl_track.columns["GenreId"] == genre_id)\
            .get()
        
        # Assertion checks that the where condition has been applied to
        # the results of the query.
        for track in q.execute():
            self.assertEqual(genre_id, track.GenreId)
    
    def test_nestedQueryInWhereClause(self):
        tbl_album = self.tables["Album"]
        tbl_genre = self.tables["Genre"]
        tbl_track = self.tables["Track"]
        
        genre_id = self.db.query(tbl_genre)\
            .where(tbl_genre.columns["Name"] == "Alternative & Punk")\
            .get().execute()[0].GenreId
        
        
        track_query = self.db.query(tbl_track.columns["AlbumId"])\
            .where(tbl_track.columns["GenreId"] == genre_id).get()
        
        album_query = self.db.query(tbl_album.columns["AlbumId"])\
                .where(
                    In_(
                        tbl_album.columns["AlbumId"],
                        self.db.query(tbl_track.columns["AlbumId"])\
                            .where(tbl_track.columns["GenreId"] == genre_id).get()
                    )
                ).get()
        
        albums = album_query.execute()
        tracks = track_query.execute()
        album_ids = set(row.AlbumId for row in tracks)
        self.assertEqual(len(albums), len(album_ids))
        for row in albums:
            self.assertTrue(row.AlbumId in album_ids)
    
    def test_aliasTable(self):
        tbl_album = self.tables["Album"]
        tbl_artist = self.tables["Artist"]
        
        artist_id = self.db.query(tbl_artist.columns["ArtistId"])\
            .where(Equal_(tbl_artist.columns["Name"], "Queen"))\
            .get().execute()[0].ArtistId
        
        musician = tbl_artist.as_("Musician")
        q = self.db.query(musician).where(Equal_(musician.columns["ArtistId"], Value(artist_id))).get()
        
        for row in q.execute():
            self.assertTrue(hasattr(row, "ArtistId"))
            self.assertTrue(hasattr(row, "Name"))
            self.assertEqual(artist_id, row.ArtistId)
    
    def test_selectFromQuery(self):
        tbl_album = self.tables["Album"]
        tbl_artist = self.tables["Artist"]
        
        artist_id = self.db.query(tbl_artist.columns["ArtistId"])\
            .where(Equal_(tbl_artist.columns["Name"], "Queen"))\
            .get().execute()[0].ArtistId
        
        inner_q = self.db.query(tbl_album.columns["ArtistId"], tbl_album.columns["Title"])\
            .where(Equal_(tbl_album.columns["ArtistId"], Value(artist_id))).get()
        
        q = self.db.query(inner_q.as_("q")).get()
        
        for row in q.execute():
            self.assertTrue(hasattr(row, "ArtistId"))
            self.assertTrue(hasattr(row, "Title"))
            self.assertEqual(artist_id, row.ArtistId)
    
    def test_groupBy(self):
        tbl_track = self.tables["Track"]
        
        q = self.db.query(tbl_track.columns["GenreId"], Count_(tbl_track.columns["TrackId"]).as_("TrackCount"))\
            .group_by(tbl_track.columns["GenreId"]).get()
        
        for row in q.execute():
            self.assertTrue(hasattr(row, "GenreId"))
            self.assertTrue(hasattr(row, "TrackCount"))
    
    def test_having(self):
        tbl_track = self.tables["Track"]
        
        q = self.db.query(tbl_track.columns["GenreId"], Count_(tbl_track.columns["TrackId"]).as_("TrackCount"))\
            .group_by(tbl_track.columns["GenreId"])\
            .having(Count_(tbl_track.columns["TrackId"]) > 25).get()
        
        for row in q.execute():
            self.assertTrue(hasattr(row, "GenreId"))
            self.assertTrue(hasattr(row, "TrackCount"))
            self.assertLess(25, row.TrackCount,
                "The track count should be greater than specified in the "
                "having clause."
            )
    
    def test_havingMustHaveGroupBy(self):
        tbl_track = self.tables["Track"]
        
        with self.assertRaises(QueryError):
            self.db.query(tbl_track.columns["GenreId"], Count_(tbl_track.columns["TrackId"]).as_("TrackCount"))\
                .having(Count_(tbl_track.columns["TrackId"]) > 25).get()
    
    def test_orderByAsc(self):
        tbl_artist = self.tables["Artist"]
        
        q = self.db.query(tbl_artist.columns["Name"])\
            .order_by(tbl_artist.columns["Name"]).get()
        
        rows = q.execute()
        prev_name = rows[0].Name
        for row in rows:
            self.assertLessEqual(prev_name, row.Name)
            prev_name = row.Name
    
    def test_orderByDesc(self):
        tbl_artist = self.tables["Artist"]
        
        q = self.db.query(tbl_artist.columns["Name"])\
            .order_by(tbl_artist.columns["Name"], ascending=False).get()
        
        rows = q.execute()
        prev_name = rows[0].Name
        for row in rows:
            self.assertGreaterEqual(prev_name, row.Name)
            prev_name = row.Name
    
    def test_orderByNullsFirst(self):
        tbl_track = self.tables["Track"]
        
        q = self.db.query(tbl_track.columns["Composer"])\
            .order_by(tbl_track.columns["Composer"], nulls="first")\
            .get()
        
        seen_value = False
        for row in q.execute():
            if not seen_value and row.Composer is not None:
                seen_value = True
            self.assertEqual(row.Composer is not None, seen_value)
    
    def test_orderByNullsLast(self):
        tbl_track = self.tables["Track"]
        
        q = self.db.query(tbl_track.columns["Composer"])\
            .order_by(tbl_track.columns["Composer"], nulls="last")\
            .get()
        
        seen_null = False
        for row in q.execute():
            if not seen_null and row.Composer is None:
                seen_null = True
            self.assertEqual(row.Composer is None, seen_null)
    
    def test_limit(self):
        limit_amount = 5
        
        tbl_track = self.tables["Track"]
        
        q = self.db.query(tbl_track.columns["Name"]).get()
        
        rows = q.execute(limit=limit_amount)
        self.assertLessEqual(len(rows), limit_amount,
            "Number of rows should not be more than the limit amount.")
    
    def test_limitAndOffset(self):
        limit_amount = 100
        tbl_track = self.tables["Track"]
        
        q0 = self.db.query(tbl_track.columns["TrackId"])\
            .order_by(tbl_track.columns["TrackId"])\
            .get()
        q1 = self.db.query(tbl_track.columns["TrackId"])\
            .order_by(tbl_track.columns["TrackId"])\
            .get()
        
        id_set = set(r.TrackId for r in q0.execute(limit=limit_amount))
        
        for row in q1.execute(limit_amount, limit_amount):
            self.assertTrue(row.TrackId not in id_set,
                "Using offset should result in different data being "
                "returned than that of a non-offset query."
            )
    
    def test_distinct(self):
        # Uses album 73 (Eric Clapton Unplugged) because it has multiple genres
        # of track on the album. It just seems a bit less trivial than most
        # albums as a test case.
        album_id = 73
        tbl_track = self.tables["Track"]
        
        q0 = self.db.query(tbl_track.columns["GenreId"])\
            .where(tbl_track.columns["AlbumId"] == album_id).get()
        
        q1 = self.db.query(tbl_track.columns["GenreId"])\
            .where(tbl_track.columns["AlbumId"] == album_id)\
            .distinct().get()
        
        genres0 = set(row.GenreId for row in q0.execute())
        genres1 = [row.GenreId for row in q1.execute()]
        self.assertEqual(len(genres0), len(genres1),
            "Set of all genres in the album should be the same size as "
            "the list of genres retrieved with SELECT DISTINCT."
        )
    
    def test_innerJoin(self):
        tbl_album = self.tables["Album"]
        tbl_track = self.tables["Track"]
        
        tbl_joinAlbumTrack = InnerJoin(tbl_album, tbl_track, using=["AlbumId"])
        
        q = self.db.query(
            tbl_joinAlbumTrack.left,
            tbl_joinAlbumTrack.right["Name"]).get()
        
        for row in q.execute():
            self.assertEqual(4, len(row))
            self.assertTrue(hasattr(row, "AlbumId"))
            self.assertTrue(hasattr(row, "Title"))
            self.assertTrue(hasattr(row, "ArtistId"))
            self.assertTrue(hasattr(row, "Name"))
    
    def test_leftOuterJoin(self):
        tbl_track = self.tables["Track"]
        tbl_playlist_track = self.tables["PlaylistTrack"]
        
        tbl_leftJoinTrackPlaylistTrack = LeftJoin(tbl_track, tbl_playlist_track, using=["TrackId"])
        
        q = self.db.query(
            tbl_leftJoinTrackPlaylistTrack.left["TrackId"],
            tbl_leftJoinTrackPlaylistTrack.right["PlaylistId"]
        ).get()
        
        num_tracks = len(self.db.query(tbl_track.columns["TrackId"]).distinct().get().execute())
        
        rows = q.execute()
        self.assertGreaterEqual(len(rows), num_tracks)
        for row in rows:
            self.assertTrue(hasattr(row, "TrackId"))
            self.assertNotEqual(row.TrackId, None)
            self.assertTrue(hasattr(row, "PlaylistId"))
    
    def test_rightOuterJoin(self):
        tbl_genre = self.tables["Genre"]
        tbl_track = self.tables["Track"]
        
        tbl_rightJoinTrackGenre = RightJoin(tbl_track, tbl_genre, using=["GenreId"])
        
        q = self.db.query(
            tbl_rightJoinTrackGenre.left["TrackId"],
            tbl_rightJoinTrackGenre.right["GenreId"]
        ).get()
        
        num_genres = len(self.db.query(tbl_genre.columns["GenreId"]).distinct().get().execute())
        
        rows = q.execute()
        self.assertGreaterEqual(len(rows), num_genres)
        for row in rows:
            self.assertTrue(hasattr(row, "TrackId"))
            self.assertTrue(hasattr(row, "GenreId"))
            self.assertNotEqual(row.GenreId, None)
    
    def test_fullOuterJoin(self):
        tbl_genre = self.tables["Genre"]
        tbl_track = self.tables["Track"]
        
        tbl_rightJoinTrackGenre = FullJoin(tbl_track, tbl_genre, using=["GenreId"])
        
        q = self.db.query(
            tbl_rightJoinTrackGenre.left["TrackId"],
            tbl_rightJoinTrackGenre.right["GenreId"]
        ).get()
        
        num_tracks = len(self.db.query(tbl_track.columns["TrackId"]).distinct().get().execute())
        num_genres = len(self.db.query(tbl_track.columns["GenreId"]).distinct().get().execute())
        
        rows = q.execute()
        self.assertGreaterEqual(len(rows), num_tracks)
        self.assertGreaterEqual(len(rows), num_genres)
        for row in rows:
            self.assertTrue(hasattr(row, "TrackId"))
            self.assertTrue(hasattr(row, "GenreId"))
    
    def test_crossJoin(self):
        tbl_playlist = self.tables["Playlist"]
        tbl_track = self.tables["Track"]
        
        playlistRecordCount = self.db.query()\
            .from_(tbl_playlist)\
            .select(RecordCount())\
            .get().execute()[0][0]
        
        trackRecordCount = self.db.query()\
            .from_(tbl_track)\
            .select(RecordCount())\
            .get().execute()[0][0]
        
        q = self.db.query()\
            .from_(CrossJoin(tbl_playlist, tbl_track))\
            .select(RecordCount().as_("RecordCount"))\
            .get()
        
        joinSizeRow = q.execute()[0]
        
        self.assertEqual(playlistRecordCount * trackRecordCount, joinSizeRow.RecordCount,
            "The cross join should contain as many records as "
            "the number of playlists times the number of tracks."
        )
    
    def test_joinOn(self):
        tbl_album = self.tables["Album"]
        tbl_track = self.tables["Track"]
        
        tbl_joinAlbumTrack = InnerJoin(tbl_album, tbl_track,
            on=[Equal_(tbl_album.columns["AlbumId"], tbl_track.columns["AlbumId"])]
        )
        
        q = self.db.query(
            tbl_joinAlbumTrack.left,
            tbl_joinAlbumTrack.right["AlbumId"].as_("TrackAlbumId"),
            tbl_joinAlbumTrack.right["Name"]).get()
        
        for row in q.execute():
            self.assertEqual(5, len(row))
            self.assertTrue(hasattr(row, "AlbumId"))
            self.assertTrue(hasattr(row, "TrackAlbumId"))
            self.assertTrue(hasattr(row, "Title"))
            self.assertTrue(hasattr(row, "ArtistId"))
            self.assertTrue(hasattr(row, "Name"))
            self.assertEqual(row.AlbumId, row.TrackAlbumId)
    
    def test_multipleJoins(self):
        tbl_album = self.tables["Album"]
        tbl_artist = self.tables["Artist"]
        tbl_track = self.tables["Track"]
        
        tbl_joinAlbumTrack = InnerJoin(tbl_album, tbl_track, using=["AlbumId"])
        tbl_joinArtistAlbumTrack = InnerJoin(tbl_artist, tbl_joinAlbumTrack, using=["ArtistId"])
        
        q = self.db.query(
            tbl_joinArtistAlbumTrack.tables["Artist"]["ArtistId"],
            tbl_joinArtistAlbumTrack.tables["Album"]["ArtistId"].as_("AlbumArtistId"),
            tbl_joinArtistAlbumTrack.tables["Album"]["AlbumId"],
            tbl_joinArtistAlbumTrack.tables["Track"]["Name"].as_("TrackName")
        ).get()
        
        for row in q.execute():
            self.assertTrue(hasattr(row, "ArtistId"))
            self.assertTrue(hasattr(row, "AlbumArtistId"))
            self.assertTrue(hasattr(row, "AlbumArtistId"))
            self.assertTrue(hasattr(row, "TrackName"))
            self.assertEqual(row.ArtistId, row.AlbumArtistId)
    
    def test_setQueryParamValue(self):
        tbl_genre = self.tables["Genre"]
        tbl_track = self.tables["Track"]
        
        genres = self.db.query(tbl_genre).get().execute(2)
        
        genre1_id = genres[0].GenreId
        genre2_id = genres[1].GenreId
        
        genre_id_param = Value(genre1_id, param_name="genre_id")
        
        q = self.db.query(tbl_track.columns["GenreId"])\
            .where(tbl_track.columns["GenreId"] == genre_id_param)\
            .get()
        
        # Assertion checks that the where condition has been applied to
        # the results of the query.
        for track in q.execute():
            self.assertEqual(genre1_id, track.GenreId)
        
        q.set_param("genre_id", genre2_id)
        
        for track in q.execute():
            self.assertEqual(genre2_id, track.GenreId)
    
    def test_queryBuilderClone(self):
        tbl_track = self.tables["Track"]
        
        qbd_track = self.db.query(
            tbl_track.columns["Name"], tbl_track.columns["GenreId"])
        
        qbd_track_clone = qbd_track.clone()\
            .select(tbl_track.columns["AlbumId"])\
            .where(tbl_track.columns["GenreId"] == 2)
        
        qbd_track.where(tbl_track.columns["GenreId"] == 1)
        
        for row in qbd_track.get().execute():
            self.assertTrue(hasattr(row, "Name"))
            self.assertFalse(hasattr(row, "AlbumId"))
            self.assertEqual(row.GenreId, 1)
        
        for row in qbd_track_clone.get().execute():
            self.assertTrue(hasattr(row, "Name"))
            self.assertTrue(hasattr(row, "AlbumId"))
            self.assertEqual(row.GenreId, 2)
