from core.models.crawlingtask import Crawlingtask
from core.models.artist import Artist
from core.models.album import Album
from core.models.datasource import DataSource
from core.models.album_track import Album_Track
from core.models.data_source_format_master import DataSourceFormatMaster
from core.models.crawlingtask_action_master import V4CrawlingTaskActionMaster
from core.models.itunes_album_tracks_release import ItunesRelease
from core.models.track import Track

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, aliased
from sqlalchemy import func, union, distinct, desc, and_, or_, tuple_, extract
from sqlalchemy import text
from core.mysql_database_connection.sqlalchemy_create_engine import SQLALCHEMY_DATABASE_URI
from typing import Optional, Tuple, Dict, List
from sqlalchemy.orm import aliased
from core.crud.get_df_from_query import get_df_from_query


from datetime import date
import time

from core.crud.sqlalchemy import get_compiled_raw_mysql
import pandas as pd

engine = create_engine(SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


def count_datasource_by_artistname_formatid(artist_name: str, formatid: str):
    count_datasource_by_artistname_formatid = (db_session.query(
        ItunesRelease.album_uuid,
        ItunesRelease.itunes_url,
        ItunesRelease.track_seq,
        ItunesRelease.duration,
        Track.id.label("trackid"),
        DataSource.id.label("Datasourceid")
    )
                                               .select_from(ItunesRelease)
                                               .join(Track, and_(Track.title == ItunesRelease.track_title,
                                                                 Track.artist == ItunesRelease.track_artist,
                                                                 Track.valid == 1))
                                               .join(DataSource, and_(DataSource.track_id == Track.id,
                                                                      DataSource.valid == 1,
                                                                      DataSource.format_id == formatid,
                                                                      DataSource.format_id != '',
                                                                      DataSource.source_name == 'YouTube'))
                                               .filter(or_(ItunesRelease.album_artist.like("%" + artist_name + "%"),
                                                           ItunesRelease.track_artist.like("%" + artist_name + "%")))
                                               .group_by(Track.id, DataSource.id)
                                               ).all()
    count = len(count_datasource_by_artistname_formatid)
    return count


def get_datasource_by_artistname_formatid(artist_name: str, formatid: str):
    get_datasource_by_artistname_formatid = (db_session.query(
        ItunesRelease.album_uuid,
        ItunesRelease.album_title,
        ItunesRelease.album_artist,
        ItunesRelease.itunes_url,
        ItunesRelease.track_seq,
        ItunesRelease.duration,
        (extract('hour', ItunesRelease.duration) * 3600000 + extract('minute',
                                                                     ItunesRelease.duration) * 60000 + extract('second',
                                                                                                               ItunesRelease.duration) * 1000).label(
            "DurationMs"),
        Track.id.label("trackid"),
        Track.title.label("track_title"),
        Track.artist.label("track_artist"),
        DataSource.id.label("datasource_id"),
        DataSource.format_id.label("FormatID"),
        DataSource.source_uri.label("SourceURI")
    )
                                             .select_from(ItunesRelease)
                                             .join(Track, and_(Track.title == ItunesRelease.track_title,
                                                               Track.artist == ItunesRelease.track_artist,
                                                               Track.valid == 1))
                                             .join(DataSource, and_(DataSource.track_id == Track.id,
                                                                    DataSource.valid == 1,
                                                                    DataSource.format_id == formatid,
                                                                    DataSource.format_id != '',
                                                                    DataSource.source_name == 'YouTube'))
                                             .filter(or_(ItunesRelease.album_artist.like("%" + artist_name + "%"),
                                                         ItunesRelease.track_artist.like("%" + artist_name + "%")))
                                             .order_by(Track.title.asc(), Track.artist, ItunesRelease.album_uuid,
                                                       ItunesRelease.track_seq.asc())
                                             .group_by(Track.id, DataSource.id)
                                             )
    return get_datasource_by_artistname_formatid


def get_crawlingtask_youtube_info(objectid: str, PIC: str, actionid: str):
    get_crawlingtask_info = (db_session.query(
        Crawlingtask.id,
        Crawlingtask.objectid,
        func.json_extract(Crawlingtask.taskdetail, "$.youtube_url").label(
            "youtube_url"),
        func.json_extract(Crawlingtask.taskdetail, "$.when_exists").label(
            "when_exists"),
        func.json_extract(Crawlingtask.taskdetail, "$.data_source_format_id").label(
            "data_source_format_id"),
        Crawlingtask.status

    )
        .select_from(Crawlingtask)
        .filter(Crawlingtask.objectid == objectid,
                Crawlingtask.actionid == actionid,
                func.json_extract(Crawlingtask.taskdetail, "$.PIC") == PIC,
                )
        .order_by(
        Crawlingtask.created_at.desc())
    ).first()
    return get_crawlingtask_info


def get_crawlingtask_info(objectid: str, PIC: str, actionid: str):

    if actionid == V4CrawlingTaskActionMaster.ARTIST_ALBUM_IMAGE:
        url = "url"
    else:
        url = "youtube_url"

    get_crawlingtask_info = (db_session.query(
        Crawlingtask.id,
        Crawlingtask.objectid,
        func.json_extract(Crawlingtask.taskdetail, f"$.{url}").label(
            "url"),
        func.json_extract(Crawlingtask.taskdetail, "$.when_exists").label(
            "when_exists"),
        Crawlingtask.status

    )
        .select_from(Crawlingtask)
        .filter(Crawlingtask.objectid == objectid,
                Crawlingtask.actionid == actionid,
                func.json_extract(Crawlingtask.taskdetail, "$.PIC") == PIC,
                # to delete
                # func.json_extract(Crawlingtask.taskdetail, "$.data_source_format_id") == "1A67A5F1E0D84FB9B48234AE65086375",
                )
        .order_by(
        Crawlingtask.created_at.desc())
    ).first()
    return get_crawlingtask_info


def get_crawlingtask_status(gsheet_name: str, sheet_name: str, actionid: str):
    if actionid == V4CrawlingTaskActionMaster.ARTIST_ALBUM_IMAGE:
        url = "url"
    else:
        url = "youtube_url"

    crawl_artist_image_status = (db_session.query(
        Crawlingtask.id,
        Crawlingtask.objectid,
        func.json_extract(Crawlingtask.taskdetail, f"$.{url}").label(
            f"{url}"),
        func.json_extract(Crawlingtask.taskdetail, "$.when_exists").label(
            "when_exists"),
        Crawlingtask.status,
        func.json_extract(Crawlingtask.ext, "$.message").label(
            "message")
    )
                                 .select_from(Crawlingtask)
                                 .filter(
        func.json_extract(Crawlingtask.taskdetail, "$.PIC") == f"{gsheet_name}_{sheet_name}",
        Crawlingtask.actionid == actionid)
                                 .order_by(Crawlingtask.objectid, Crawlingtask.created_at.desc())
                                 )
    return crawl_artist_image_status


def get_s11_crawlingtask_info(pic: str):
    # JOIN same table with aliases on SQLAlchemy
    crawlingtasks_06 = aliased(Crawlingtask, name='crawlingtasks_06')
    crawlingtasks_E5 = aliased(Crawlingtask, name='crawlingtasks_E5')

    s11_crawlingtask_info = (db_session.query(
        func.json_extract(crawlingtasks_06.taskdetail, f"$.album_id").label("itune_album_id"),
        crawlingtasks_06.id.label("06_id"),
        crawlingtasks_06.status.label("06_status"),
        crawlingtasks_E5.id.label("E5_id"),
        crawlingtasks_E5.status.label("E5_status")
    )
                                 .select_from(crawlingtasks_06)
                                 .outerjoin(crawlingtasks_E5,
                                            # crawlingtasks_E5.id == func.json_extract(crawlingtasks_06.ext, "$.itunes_track_task_id"), #performance query problem
                                            text("crawlingtasks_E5.id = crawlingtasks_06.ext ->> '$.itunes_track_task_id'")
                                            )).filter(
        crawlingtasks_06.actionid == "9C8473C36E57472281A1C7936108FC06",
        func.json_extract(crawlingtasks_06.taskdetail, "$.PIC") == pic,
    ).order_by(
        crawlingtasks_06.created_at.desc())
    return s11_crawlingtask_info


def get_track_title_track_artist_by_ituneid_and_seq(itune_album_id: str, seq: str):
    get_track_title_track_artist_by_ituneid_and_seq = (db_session.query(
        # ItunesRelease.album_uuid,
        # ItunesRelease.album_title,

    )
                                             .select_from(Album)
                                             .join(Album_Track, Album.uuid == Album_Track.album_uuid,)
                                             .join(Track, and_(Album_Track.track_id == Track.id,
                                                                Track.valid == 1))
                                             .filter(Album.valid == 1)
                                             )
    return get_datasource_by_artistname_formatid

if __name__ == "__main__":
    start_time = time.time()
    pd.set_option("display.max_rows", None, "display.max_columns", 30, 'display.width', 500)
    # db_crawlingtasks = get_s11_crawlingtask_info(pic="NewClassic 24.05.2021_S_11")
    # k = get_compiled_raw_mysql(db_crawlingtasks)
    # print(k)
    # # print(k)
    # # for db_crawlingtask in db_crawlingtasks:
    # #     print(db_crawlingtask.album_id)
    df = get_df_from_query(query=get_s11_crawlingtask_info(pic="NewClassic 25.05.2021_S_11")).astype(str)
    print(df.dtypes)
    print(df)
    print("\n --- total time to process %s seconds ---" % (time.time() - start_time))






#     print(k)
#     print("--- %s seconds ---" % (time.time() - start_time))
