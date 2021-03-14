from google_spreadsheet_api.function import get_df_from_speadsheet, get_list_of_sheet_title, update_value, \
    creat_new_sheet_and_update_data_from_df, get_gsheet_name
from google_spreadsheet_api.create_new_sheet_and_update_data_from_df import creat_new_sheet_and_update_data_from_df
from tools.data_lake_standard import crawl_mp3_mp4
from tools.crawlingtask import sheet_type

from core.crud.sql.datasource import get_datasourceids_from_youtube_url_and_trackid, related_datasourceid, \
    get_youtube_info_from_trackid
from core.models.data_source_format_master import DataSourceFormatMaster
from core.crud.get_df_from_query import get_df_from_query
from youtube_dl_fuction.fuctions import get_raw_title_uploader_from_youtube_url

from itertools import chain
import pandas as pd
import time
from colorama import Fore, Style
from core import query_path
from support_function.text_similarity.text_similarity import get_token_set_ratio
from numpy import random
import numpy as np
from core.crud.sql.query_supporter import count_datasource_by_artistname_formatid, get_datasource_by_artistname_formatid

def check_youtube_url_mp3(gsheet_id: str):
    '''
    TrackID	Memo	URL_to_add	Type	Assignee
                                        no need to check
    not null	added	length = 43	    C/D/Z
    not null	not found	none	none
    :return:
    '''
    sheet_name = 'MP_3'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)

    original_df['len'] = original_df['url_to_add'].apply(lambda x: len(x))
    youtube_url_mp3 = original_df[['track_id', 'Memo', 'url_to_add', 'len', 'Type', 'Assignee']]

    check_youtube_url_mp3 = youtube_url_mp3[~
    ((
             (youtube_url_mp3['track_id'] != '')
             & (youtube_url_mp3['Memo'] == 'added')
             & (youtube_url_mp3['len'] == 43)
             & (youtube_url_mp3['Type'].isin(["c", "d", "z"]))
     ) |
     (
             (youtube_url_mp3['track_id'] != '')
             & (youtube_url_mp3['Memo'] == 'not found')
             & (youtube_url_mp3['url_to_add'] == 'none')
             & (youtube_url_mp3['Type'] == 'none')
     ) |
     (

         (youtube_url_mp3['Assignee'] == 'no need to check')
     ))
    ]

    return check_youtube_url_mp3.track_id.str.upper()


def check_youtube_url_mp4(gsheet_id: str):
    '''
        TrackID	Memo	URL_to_add	Assignee
                                    no need to check
        not null	ok	null
        not null	added	length = 43
        not null	not found	none
        not null	not ok	length = 43
        not null	not ok	none
    :return:
    '''

    sheet_name = 'MP_4'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)
    original_df['len'] = original_df['url_to_add'].apply(lambda x: len(x))
    youtube_url_mp4 = original_df[['track_id', 'Memo', 'url_to_add', 'len', 'Assignee']]

    check_youtube_url_mp4 = youtube_url_mp4[~
    ((
             (youtube_url_mp4['track_id'] != '')
             & (youtube_url_mp4['Memo'] == 'ok')
             & (youtube_url_mp4['url_to_add'] == '')
     ) |
     (
             (youtube_url_mp4['track_id'] != '')
             & (youtube_url_mp4['Memo'] == 'added')
             & (youtube_url_mp4['len'] == 43)
     ) |
     (
             (youtube_url_mp4['track_id'] != '')
             & (youtube_url_mp4['Memo'] == 'not found')
             & (youtube_url_mp4['url_to_add'] == 'none')
     ) |
     (
             (youtube_url_mp4['track_id'] != '')
             & (youtube_url_mp4['Memo'] == 'not ok')
             & (youtube_url_mp4['len'] == 43)
     ) |
     (
             (youtube_url_mp4['track_id'] != '')
             & (youtube_url_mp4['Memo'] == 'not ok')
             & (youtube_url_mp4['url_to_add'] == 'none')
     ) |
     (youtube_url_mp4['Assignee'] == 'no need to check')
     )
    ]
    return check_youtube_url_mp4.track_id.str.upper()


def check_version(gsheet_id: str):
    '''
    TrackID	    URL         	Remix_Artist
    not null	length = 43	    not null
    not null	null	        null

    TrackID	    URL2	        Venue           Live_year
    not null	length = 43	    not null        null hoặc nằm trong khoảng từ 1950 đến 2030
    not null	null	        null            null
    '''

    sheet_name = 'Version_done'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)

    original_df['len_remix_url'] = original_df['Remix_url'].apply(lambda x: len(x))
    original_df['len_live_url'] = original_df['Live_url'].apply(lambda x: len(x))
    original_df['Live_year'] = pd.to_numeric(original_df.Live_year, errors='coerce').astype('Int64').fillna(0)

    youtube_url_version = original_df[
        ['track_id', 'Remix_url', 'Remix_artist', 'Live_url', 'Live_venue', 'len_remix_url', 'len_live_url',
         'Live_year']]

    check_version = youtube_url_version[~
    (((
              (youtube_url_version['track_id'] != '')
              & (youtube_url_version['len_remix_url'] == 43)
              & (youtube_url_version['Remix_artist'] != '')
      ) |
      (
              (youtube_url_version['track_id'] != '')
              & (youtube_url_version['Remix_url'] == '')
              & (youtube_url_version['Remix_artist'] == '')
      )) &
     ((
              (youtube_url_version['track_id'] != '')
              & (youtube_url_version['len_live_url'] == 43)
              & (youtube_url_version['Live_venue'] != '')
              & ((youtube_url_version['Live_year'] == 0) | (
              (1950 <= original_df['Live_year']) & (original_df['Live_year'] <= 2030)))
      ) |
      (
              (youtube_url_version['track_id'] != '')
              & (youtube_url_version['Live_url'] == '')
              & (youtube_url_version['Live_venue'] == '')
              & (youtube_url_version['Live_year'] == 0)
      )))
    ]
    return check_version.track_id.str.upper()


def check_album_image(gsheet_id: str):
    '''
        AlbumUUID	Memo	URL_to_add	Assignee
                                        no need to check
        not null	ok	null
        not null	added	not null
        not null	not found	none
    :return:
    '''
    sheet_name = 'Album_image'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)
    album_image = original_df[['Album_uuid', 'Memo', 'url_to_add', 'Assignee']]

    check_album_image = album_image[~
    ((
             (album_image['Album_uuid'] != '')
             & (album_image['Memo'] == 'ok')
             & (album_image['url_to_add'] == '')
     ) |
     (
             (album_image['Album_uuid'] != '')
             & (album_image['Memo'] == 'added')
             & (album_image['url_to_add'] != '')
     ) |
     (
             (album_image['Album_uuid'] != '')
             & (album_image['Memo'] == 'not found')
             & (album_image['url_to_add'] == 'none')
     ) |
     (
         (album_image['Assignee'] == 'no need to check')
     ))
    ]

    return check_album_image.Album_uuid.str.upper()


def check_artist_image(gsheet_id: str):
    '''
        ArtistTrackUUID	Memo	URL_to_add	Assignee
                                            no need to check
        not null	ok	null
        not null	added	not null
    :return:
    '''
    sheet_name = 'Artist_image'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)
    artist_image = original_df[['Artist_uuid', 'Memo', 'url_to_add', 'Assignee']]

    check_artist_image = artist_image[~
    ((
             (artist_image['Artist_uuid'] != '')
             & (artist_image['Memo'] == 'ok')
             & (artist_image['url_to_add'] == '')
     ) |
     (
             (artist_image['Artist_uuid'] != '')
             & (artist_image['Memo'] == 'added')
             & (artist_image['url_to_add'] != '')
     ) |
     (
         (artist_image['Assignee'] == 'no need to check')
     ))
    ]
    return check_artist_image.Artist_uuid.str.upper()


def check_album_wiki(gsheet_id: str):
    '''
        AlbumUUID	Memo	URL_to_add	Content_to_add	Assignee
                                                        no need to check
        not null	ok	null	null
        not null	added	https://en.wikipedia.org/%	not null
        not null	not found	none	none
        not null	not ok	https://en.wikipedia.org/%	not null
        not null	not ok	none	none
    :return:
    '''
    sheet_name = 'Album_wiki'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)
    album_wiki = original_df[['Album_uuid', 'Memo', 'url_to_add', 'Content_to_add', 'Assignee']]

    check_album_wiki = album_wiki[~
    ((
             (album_wiki['Album_uuid'] != '')
             & (album_wiki['Memo'] == 'ok')
             & (album_wiki['url_to_add'] == '')
             & (album_wiki['Content_to_add'] == '')
     ) |
     (
             (album_wiki['Album_uuid'] != '')
             & (album_wiki['Memo'] == 'added')
             & (album_wiki['url_to_add'].str[:25] == 'https://en.wikipedia.org/')
             & (album_wiki['Content_to_add'] != '')
     ) |
     (
             (album_wiki['Album_uuid'] != '')
             & (album_wiki['Memo'] == 'not found')
             & (album_wiki['url_to_add'] == 'none')
             & (album_wiki['Content_to_add'] == 'none')
     ) |
     (
             (album_wiki['Album_uuid'] != '')
             & (album_wiki['Memo'] == 'not ok')
             & (album_wiki['url_to_add'].str[:25] == 'https://en.wikipedia.org/')
             & (album_wiki['Content_to_add'] != '')
     ) |
     (
             (album_wiki['Album_uuid'] != '')
             & (album_wiki['Memo'] == 'not ok')
             & (album_wiki['url_to_add'] == 'none')
             & (album_wiki['Content_to_add'] == 'none')
     ) |
     (
         (album_wiki['Assignee'] == 'no need to check')
     ))
    ]
    return check_album_wiki.Album_uuid.str.upper()


def check_artist_wiki(gsheet_id: str):
    '''
        Artist_uuid	Memo	URL_to_add	Assignee
                    no need to check
        not null	ok	null
        not null	added	https://en.wikipedia.org/%
        not null	not found	none
        not null	not ok	https://en.wikipedia.org/%
        not null	not ok	none
    :return:
    '''

    sheet_name = 'Artist_wiki'
    original_df = get_df_from_speadsheet(gsheet_id, sheet_name).applymap(str.lower)
    artist_wiki = original_df[['Artist_uuid', 'Memo', 'url_to_add', 'Assignee']]

    check_artist_wiki = artist_wiki[~
    ((
             (artist_wiki['Artist_uuid'] != '')
             & (artist_wiki['Memo'] == 'ok')
             & (artist_wiki['url_to_add'] == '')
     ) |
     (
             (artist_wiki['Artist_uuid'] != '')
             & (artist_wiki['Memo'] == 'added')
             & (artist_wiki['url_to_add'].str[:25] == 'https://en.wikipedia.org/')
     ) |
     (
             (artist_wiki['Artist_uuid'] != '')
             & (artist_wiki['Memo'] == 'not found')
             & (artist_wiki['url_to_add'] == 'none')
     ) |
     (
             (artist_wiki['Artist_uuid'] != '')
             & (artist_wiki['Memo'] == 'not ok')
             & (artist_wiki['url_to_add'].str[:25] == 'https://en.wikipedia.org/')
     ) |
     (
             (artist_wiki['Artist_uuid'] != '')
             & (artist_wiki['Memo'] == 'not ok')
             & (artist_wiki['url_to_add'] == 'none')
     ) |
     (
         (artist_wiki['Assignee'] == 'no need to check')
     ))
    ]
    return check_artist_wiki.Artist_uuid.str.upper()


def check_box(urls: list):
    # Check all element:
    '''
        "https://docs.google.com/spreadsheets/d/1L17AVvNANbHYyLFKXlYRBEol8nZ14pvO3_KSGlQf0WE/edit#gid=1241019472",
        "https://docs.google.com/spreadsheets/d/14tBa8mqCAXw50qcQfZsrTs70LeKIPEe9yISsXxYgQUk/edit",
    '''
    for url in urls:
        gsheet_id = get_gsheet_id_from_url(url)
        gsheet_name = get_gsheet_name(gsheet_id=gsheet_id)
        print(Fore.LIGHTYELLOW_EX + f" \n{gsheet_name}\n{url}\n" + Style.RESET_ALL)

        list_of_sheet_title = get_list_of_sheet_title(gsheet_id)
        if 'MP_3' in list_of_sheet_title:
            youtube_url_mp3 = check_youtube_url_mp3(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            youtube_url_mp3 = ["MP_3 not found"]

        if 'MP_4' in list_of_sheet_title:
            youtube_url_mp4 = check_youtube_url_mp4(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            youtube_url_mp4 = ["MP_4 not found"]

        if 'Version_done' in list_of_sheet_title:
            version = check_version(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            version = ["Version_done not found"]

        if 'Album_image' in list_of_sheet_title:
            album_image = check_album_image(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            album_image = ["Album_image not found"]

        if 'Artist_image' in list_of_sheet_title:
            artist_image = check_artist_image(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            artist_image = ["Artist_image not found"]

        if 'Album_wiki' in list_of_sheet_title:
            album_wiki = check_album_wiki(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            album_wiki = ["Album_wiki not found"]

        if 'Artist_wiki' in list_of_sheet_title:
            artist_wiki = check_artist_wiki(gsheet_id=gsheet_id).to_numpy().tolist()
        else:
            artist_wiki = ["Artist_wiki not found"]

        # Convert checking element result to df:
        items = []
        status = []
        comment = []

        dict_value = [youtube_url_mp3, youtube_url_mp4, version, album_image, artist_image, album_wiki, artist_wiki]
        dict_key = ['youtube_url_mp3', 'youtube_url_mp4', 'version', 'album_image', 'artist_image', 'album_wiki',
                    'artist_wiki']
        dict_result = dict(zip(dict_key, dict_value))
        for i, j in dict_result.items():
            if not j:
                status.append('ok')
                comment.append(None)
                items.append(i)
            else:
                status.append('not ok')
                comment.append(j)
                items.append(i)

        d = {'items': items, 'status': status, 'comment': comment}
        df = pd.DataFrame(data=d).astype(str)
        print(df)

        creat_new_sheet_and_update_data_from_df(df, gsheet_id, 'jane_to_check_result')
        return df


def process_mp3_mp4(sheet_info: dict, urls: list):
    '''
    Memo = not ok and url_to_add = 'none'
        => if not existed in related_table: set valid = -10
        => if existed in related_table:
            - set trackid = blank and formatid = blank
            - update trackcountlogs
    Memo = not ok and url_to_add not null => crawl mode replace
    Memo = added => crawl mode skip
    '''

    mp3_mp4_df = pd.DataFrame()
    for url in urls:
        gsheet_id = get_gsheet_id_from_url(url=url)

        k = check_box(urls=[url])
        check_box_filtered = k[~(
                (k['status'] == "not ok")
                & (k['comment'].str.contains('not found')))
        ]
        checking = 'not ok' in check_box_filtered.status.drop_duplicates().tolist()
        if checking == 1:
            return print("Please recheck check_box")
        else:
            sheet_name = sheet_info['sheet_name']
            original_df = get_df_from_speadsheet(gsheet_id, sheet_name)
            youtube_url = original_df[sheet_info['column_name']]
            filter_df = youtube_url[
                (youtube_url['Memo'] == 'not ok') | (youtube_url['Memo'] == 'added')].reset_index().drop_duplicates(
                subset=['track_id'],
                keep='first')  # remove duplicate df by column (reset_index before drop_duplicate: because of drop_duplicate default reset index)
            info = {"url": f"{url}", "gsheet_id": f"{gsheet_id}",
                    "gsheet_name": f"{get_gsheet_name(gsheet_id=gsheet_id)}",
                    "sheet_name": f"{sheet_name}"}
            filter_df['gsheet_info'] = f"{info}"
            mp3_mp4_df = mp3_mp4_df.append(filter_df, ignore_index=True)
    return mp3_mp4_df


def get_gsheet_id_from_url(url: str):
    url_list = url.split("/")
    gsheet_id = url_list[5]
    return gsheet_id


def get_count_datasource_by_artist_and_formatid(artist_names: list, formatid: str):
    for artist_name in artist_names:
        count = count_datasource_by_artistname_formatid(artist_name=artist_name,formatid=formatid)
        print(f"{artist_name}----{count}")


def get_df_datasource_by_artist_and_formatid(artist_names: list, formatid: str, df: object):
    formatid = formatid
    for artist_name in artist_names:
        df = df.append(
            get_df_from_query(get_datasource_by_artistname_formatid(artist_name=artist_name, formatid=formatid)).fillna(
                ""), ignore_index=True)
        print(artist_name)
        print(df)
        creat_new_sheet_and_update_data_from_df(df=df, gsheet_id=gsheet_id,
                                                new_sheet_name=f"{sheet_name}")
        print("Complete update data")


if __name__ == "__main__":
    start_time = time.time()
    pd.set_option("display.max_rows", None, "display.max_columns", 50, 'display.width', 1000)
    with open(query_path, "w") as f:
        f.truncate()
    gsheet_id = "1eO8J2qqjxgRVnc3b1EWGskVHYc1baUAmDzdqT6hIdRg"
    sheet_titles = get_list_of_sheet_title(gsheet_id= gsheet_id)
    sheet_name = "mp_3"
    if sheet_name in sheet_titles:
        df = get_df_from_speadsheet(gsheet_id=gsheet_id,sheet_name=sheet_name)
    else:
        df = pd.DataFrame()
    artists = [
        "Ray Charles",
        "Pet Shop Boys",
    ]
    formatid = DataSourceFormatMaster.FORMAT_ID_MP3_FULL
    get_df_datasource_by_artist_and_formatid(artists, formatid, df=df)

    print("--- %s seconds ---" % (time.time() - start_time))
