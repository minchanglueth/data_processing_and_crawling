from google_spreadsheet_api.function import get_df_from_speadsheet, get_list_of_sheet_title, update_value, \
    creat_new_sheet_and_update_data_from_df, get_gsheet_name

from core.crud.sql.datasource import get_datasourceids_from_youtube_url_and_trackid, related_datasourceid, \
    get_youtube_info_from_trackid
from core.crud.sql import artist, album
from core.crud.get_df_from_query import get_df_from_query
from core.crud.sql.query_supporter import get_crawlingtask_youtube_info, get_crawlingtask_info, \
    get_crawlingtask_image_status

from tools.crawlingtask import crawl_youtube, WhenExist, crawl_image, object_type, sheet_type
from core.models.data_source_format_master import DataSourceFormatMaster
from core.models.crawlingtask_action_master import V4CrawlingTaskActionMaster

import pandas as pd
import numpy as np
import time
from core import query_path
from itertools import chain
from colorama import Fore, Style
import json


def get_sheet_info_from_url(url: str):
    url_list = url.split("/")
    gsheet_id = url_list[5]
    gsheet_name = get_gsheet_name(gsheet_id=gsheet_id)
    list_of_sheet_title = get_list_of_sheet_title(gsheet_id=gsheet_id)
    return {"gsheet_id": gsheet_id, "gsheet_name": gsheet_name, "list_of_sheet_title": list_of_sheet_title}


def get_gsheet_id_from_url(url: str):
    url_list = url.split("/")
    gsheet_id = url_list[5]
    return gsheet_id


def process_image(urls: list, sheet_info: dict, sheet_name_core=None):
    '''
    ARTIST_IMAGE = {"sheet_name": "Artist_image", "column_name": ["uuid", "Memo", "url_to_add"],
                    "object_type": "artist", "sub_sheet": "artist image cant upload"}
    ALBUM_IMAGE = {"sheet_name": "Album_image", "column_name": ["uuid", "Memo", "url_to_add"],
                   "object_type": "album", "sub_sheet": "album image cant upload"}
    '''
    image_df = pd.DataFrame()
    for url in urls:
        gsheet_id = get_gsheet_id_from_url(url=url)
        list_of_sheet_title = get_list_of_sheet_title(gsheet_id)
        sub_sheet = sheet_info['sub_sheet']
        if sub_sheet in list_of_sheet_title:
            sheet_name = sub_sheet
            if get_df_from_speadsheet(gsheet_id, sheet_name).values.tolist() == [['Upload thành công 100% nhé các em ^ - ^']]:
                continue
            else:
                pass
        elif sheet_name_core is not None:
            sheet_name = sheet_name_core
        else:
            sheet_name = sheet_info['sheet_name']
            if sheet_name in list_of_sheet_title:
                pass
            else:
                continue

        original_df = get_df_from_speadsheet(gsheet_id, sheet_name)

        # Refactor column name before put into datalake
        original_df.columns = original_df.columns.str.replace('Artist_UUID', 'uuid')
        original_df.columns = original_df.columns.str.replace('Album_uuid', 'uuid')
        original_df.columns = original_df.columns.str.replace('A12', 'Memo')
        original_df.columns = original_df.columns.str.replace('s12', 'Memo')
        original_df.columns = original_df.columns.str.replace('artist_url_to_add', 'url_to_add')
        original_df.columns = original_df.columns.str.replace('objectid', 'uuid')

        if sheet_name == sub_sheet:
            original_df['Memo'] = "missing"
        else:
            original_df = original_df

        image = original_df[sheet_info['column_name']]

        filter_df = image[((image.Memo == 'missing') | (image.Memo == 'added'))  # filter df by conditions
                          & (image.url_to_add.notnull())
                          & (image.url_to_add != '')
                          ].reset_index().drop_duplicates(subset=['uuid'],
                                                          keep='first')  # remove duplicate df by column (reset_index before drop_duplicate: because of drop_duplicate default reset index)
        info = {"url": f"{url}", "gsheet_id": f"{gsheet_id}",
                "gsheet_name": f"{get_gsheet_name(gsheet_id=gsheet_id)}",
                "sheet_name": f"{sheet_name}"}
        filter_df['gsheet_info'] = f"{info}"
        image_df = image_df.append(filter_df, ignore_index=True)
    return image_df


def crawl_image_datalake(df: object, sheet_info: dict, object_type: str, when_exists: str = WhenExist.REPLACE):
    '''
    ARTIST_IMAGE = {"sheet_name": "Artist_image", "column_name": ["uuid", "Memo", "url_to_add"],
                    "object_type": "artist", "sub_sheet": "artist image cant upload"}
    ALBUM_IMAGE = {"sheet_name": "Album_image", "column_name": ["uuid", "Memo", "url_to_add"],
                   "object_type": "album", "sub_sheet": "album image cant upload"}
    '''
    row_index = df.index
    with open(query_path, "w") as f:
        for i in row_index:
            uuid = df['uuid'].loc[i]
            url = df['url_to_add'].loc[i]
            sheet_info_log = df.gsheet_info.loc[i]
            sheet_info_log = sheet_info_log.replace("'", "\"")
            gsheet_name = json.loads(sheet_info_log)['gsheet_name']
            sheet_name = json.loads(sheet_info_log)['sheet_name']
            query = crawl_image(object_type=object_type, url=url, objectid=uuid, when_exists=when_exists,
                                pic=f"{gsheet_name}_{sheet_name}")
            f.write(query)


def automate_check_crawl_image_status(gsheet_name: str, sheet_name: str):
    count = 0
    while True and count < 300:
        df1 = get_df_from_query(get_crawlingtask_image_status(gsheet_name=gsheet_name, sheet_name=sheet_name))
        result = df1[
                     (df1.status != 'complete')
                     & (df1.status != 'incomplete')
                     ].status.tolist() == []
        if result == 1:
            # print('\n', 'Checking crawlingtask status \n', df1, '\n')
            print(
                Fore.LIGHTYELLOW_EX + f"File: {gsheet_name}, sheet_name: {sheet_name} has been crawled complete already" + Style.RESET_ALL)
            break
        else:
            count += 1
            time.sleep(5)
            print(count, "-----", result)


def checking_crawlingtask_image_crawler_status(df: object):
    '''

    .filter(Crawlingtask.objectid == objectid,
             Crawlingtask.actionid == actionid,
             func.json_extract(Crawlingtask.taskdetail, "$.PIC") == PIC
    '''
    # Step 1: checking accuracy
    print("checking accuracy ")
    df = df.copy()
    # df = df.head(10)
    df.columns = df.columns.str.replace('Artist_uuid', 'uuid')
    df.columns = df.columns.str.replace('Album_uuid', 'uuid')
    df["check"] = ''
    df["status"] = ''
    row_index = df.index
    for i in row_index:
        objectid = df.uuid.loc[i]
        url = df.url_to_add.loc[i]
        sheet_info_log = df.gsheet_info.loc[i]
        sheet_info_log = sheet_info_log.replace("'", "\"")
        gsheet_name = json.loads(sheet_info_log)['gsheet_name']
        sheet_name = json.loads(sheet_info_log)['sheet_name']
        actionid = V4CrawlingTaskActionMaster.ARTIST_ALBUM_IMAGE
        PIC_taskdetail = f"{gsheet_name}_{sheet_name}"
        db_crawlingtask = get_crawlingtask_info(objectid=objectid, PIC=PIC_taskdetail, actionid=actionid)
        if db_crawlingtask:
            status = db_crawlingtask.status
            if url in db_crawlingtask.url:
                joy_check = True
            else:
                joy_check = f"file: {PIC_taskdetail}, uuid: {objectid}, crawlingtask_id: {db_crawlingtask.id}: uuid and url not match"
        else:
            joy_check = f"file: {PIC_taskdetail}, uuid: {objectid} is missing"
            status = 'not have'
        df.loc[i, 'check'] = joy_check
        df.loc[i, 'status'] = status
    k = list(set(df.check.tolist()))
    if k != [True]:
        print(df[['uuid', 'check']])

    # Step 2: autochecking status
    else:
        print("checking accuracy correctly, now checking status")
        gsheet_info_all = list(set(df.gsheet_info.tolist()))
        for gsheet_info in gsheet_info_all:
            gsheet_info = gsheet_info.replace("'", "\"")
            gsheet_name = json.loads(gsheet_info)['gsheet_name']
            sheet_name = json.loads(gsheet_info)['sheet_name']
            gsheet_id = json.loads(gsheet_info)['gsheet_id']
            automate_check_crawl_image_status(gsheet_name=gsheet_name, sheet_name=sheet_name)

            # Step 3: upload image cant crawl
            df1 = get_df_from_query(get_crawlingtask_image_status(gsheet_name=gsheet_name,
                                                                  sheet_name=sheet_name)).reset_index().drop_duplicates(
                subset=['objectid'],
                keep='first')  # remove duplicate df by column (reset_index before drop_duplicate: because of drop_duplicate default reset index)

            if sheet_info['object_type'] == "artist":
                df1['name'] = df1['objectid'].apply(lambda x: artist.get_one_by_id(artist_uuid=x).name)
            else:
                df1['title'] = df1['objectid'].apply(lambda x: album.get_one_by_id(artist_uuid=x).title)
                df1['artist'] = df1['objectid'].apply(lambda x: album.get_one_by_id(artist_uuid=x).artist)

            joy = df1[
                      (df1.status == 'incomplete')
                  ].status.tolist() == []

            if joy:
                raw_df_to_upload = {'status': ['Upload thành công 100% nhé các em ^ - ^']}
                df_to_upload = pd.DataFrame(data=raw_df_to_upload)
            else:
                df_to_upload = df1[(df1.status == 'incomplete')]
            print(df_to_upload)

            new_sheet_name = sheet_info['sub_sheet']
            print(f"{gsheet_id}----{new_sheet_name}")
            creat_new_sheet_and_update_data_from_df(df_to_upload, gsheet_id, new_sheet_name)


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

def crawl_mp3_mp4(df: object, sheet_info: dict):
    row_index = df.index
    old_youtube_url_column_name = sheet_info['column_name'][2]
    datasource_format_id = sheet_info['fomatid']
    with open(query_path, "a+") as f:
        for i in row_index:
            memo = df.Memo.loc[i]
            new_youtube_url = df.url_to_add.loc[i]
            track_id = df.track_id.loc[i]
            old_youtube_url = df[old_youtube_url_column_name].loc[i]
            query = ""
            sheet_info_log = df.gsheet_info.loc[i]
            sheet_info_log = sheet_info_log.replace("'", "\"")
            gsheet_name = json.loads(sheet_info_log)['gsheet_name']
            sheet_name = json.loads(sheet_info_log)['sheet_name']
            gsheet_id = json.loads(sheet_info_log)['gsheet_id']

            if memo == "not ok" and new_youtube_url == "none":
                datasourceids = get_datasourceids_from_youtube_url_and_trackid(youtube_url=old_youtube_url,
                                                                               trackid=track_id,
                                                                               formatid=datasource_format_id).all()
                datasourceids_flatten_list = tuple(set(list(chain.from_iterable(datasourceids))))  # flatten list

                if datasourceids_flatten_list:
                    for datasourceid in datasourceids_flatten_list:
                        related_id_datasource = related_datasourceid(datasourceid)
                        if related_id_datasource == [(None, None, None)]:
                            query = query + f"Update datasources set valid = -10 where id = {datasourceid};\n"
                        else:
                            query = query + f"UPDATE datasources SET trackid = '', FormatID = ''  where id = '{datasourceid}';\n"
                            query = query + f"UPDATE datasources SET updatedAt = NOW() WHERE trackid = '{track_id}';\n"

                else:
                    query = query + f"--not existed datasourceid searched by youtube_url: {old_youtube_url}, trackid:  {track_id}, format_id: {datasource_format_id} in gssheet_name: {gsheet_name}, gsheet_id: {gsheet_id}, sheet_name: {sheet_name} ;\n"

            elif memo == "not ok" and new_youtube_url != "none":
                query = query + crawl_youtube(track_id=track_id, youtube_url=new_youtube_url,
                                              format_id=sheet_info.get('fomatid'),
                                              when_exist=WhenExist.REPLACE, pic=f"{gsheet_name}_{sheet_name}")
            elif memo == "added":
                query = query + crawl_youtube(track_id=track_id, youtube_url=new_youtube_url,
                                              format_id=sheet_info.get('fomatid'),
                                              when_exist=WhenExist.SKIP, pic=f"{gsheet_name}_{sheet_name}")
            f.write(query)


def checking_crawlingtask_mp3_mp4_crawler_status(df: object):
    '''

    .filter(Crawlingtask.objectid == objectid,
             Crawlingtask.actionid == actionid,
             func.json_extract(Crawlingtask.taskdetail, "$.PIC") == PIC
    '''
    # Step 1: checking accuracy
    print("checking accuracy ")
    df = df.copy()
    df_crawled = df[df['Memo'] == 'added']

    df_crawled = df_crawled.head(10)
    print(df_crawled)

    row_index = df_crawled.index
    for i in row_index:
        objectid = df.track_id.loc[i]
        url = df.url_to_add.loc[i]
        sheet_info_log = df.gsheet_info.loc[i]
        sheet_info_log = sheet_info_log.replace("'", "\"")
        gsheet_name = json.loads(sheet_info_log)['gsheet_name']
        sheet_name = json.loads(sheet_info_log)['sheet_name']
        actionid = V4CrawlingTaskActionMaster.DOWNLOAD_VIDEO_YOUTUBE
        PIC_taskdetail = f"{gsheet_name}_{sheet_name}"
        print(f"{objectid}----{PIC_taskdetail}----{actionid}")
        # db_crawlingtask = get_crawlingtask_info(objectid=objectid, PIC=PIC_taskdetail, actionid=actionid)
        # print(db_crawlingtask)
        # if db_crawlingtask:
    #         status = db_crawlingtask.status
    #         if url in db_crawlingtask.url:
    #             joy_check = True
    #         else:
    #             joy_check = f"file: {PIC_taskdetail}, uuid: {objectid}, crawlingtask_id: {db_crawlingtask.id}: uuid and url not match"
    #     else:
    #         joy_check = f"file: {PIC_taskdetail}, uuid: {objectid} is missing"
    #         status = 'not have'
    #     df.loc[i, 'check'] = joy_check
    #     df.loc[i, 'status'] = status
    # k = list(set(df.check.tolist()))
    # if k != [True]:
    #     print(df[['uuid', 'check']])
    #
    # # Step 2: autochecking status
    # else:
    #     print("checking accuracy correctly, now checking status")
    #     gsheet_info_all = list(set(df.gsheet_info.tolist()))
    #     for gsheet_info in gsheet_info_all:
    #         gsheet_info = gsheet_info.replace("'", "\"")
    #         gsheet_name = json.loads(gsheet_info)['gsheet_name']
    #         sheet_name = json.loads(gsheet_info)['sheet_name']
    #         gsheet_id = json.loads(gsheet_info)['gsheet_id']
    #         automate_check_crawl_image_status(gsheet_name=gsheet_name, sheet_name=sheet_name)
    #
    #         # Step 3: upload image cant crawl
    #         df1 = get_df_from_query(get_crawlingtask_image_status(gsheet_name=gsheet_name,
    #                                                               sheet_name=sheet_name)).reset_index().drop_duplicates(
    #             subset=['objectid'],
    #             keep='first')  # remove duplicate df by column (reset_index before drop_duplicate: because of drop_duplicate default reset index)
    #
    #         if sheet_info['object_type'] == "artist":
    #             df1['name'] = df1['objectid'].apply(lambda x: artist.get_one_by_id(artist_uuid=x).name)
    #         else:
    #             df1['title'] = df1['objectid'].apply(lambda x: album.get_one_by_id(artist_uuid=x).title)
    #             df1['artist'] = df1['objectid'].apply(lambda x: album.get_one_by_id(artist_uuid=x).artist)
    #
    #         joy = df1[
    #                   (df1.status == 'incomplete')
    #               ].status.tolist() == []
    #
    #         if joy:
    #             raw_df_to_upload = {'status': ['Upload thành công 100% nhé các em ^ - ^']}
    #             df_to_upload = pd.DataFrame(data=raw_df_to_upload)
    #         else:
    #             df_to_upload = df1[(df1.status == 'incomplete')]
    #         print(df_to_upload)
    #
    #         new_sheet_name = sheet_info['sub_sheet']
    #         print(f"{gsheet_id}----{new_sheet_name}")
    #         creat_new_sheet_and_update_data_from_df(df_to_upload, gsheet_id, new_sheet_name)


if __name__ == "__main__":
    start_time = time.time()
    pd.set_option("display.max_rows", None, "display.max_columns", 30, 'display.width', 500)
    with open(query_path, "w") as f:
        f.truncate()
    urls = [
        'https://docs.google.com/spreadsheets/d/1pEZBzBwmduhZYN9k5doNbuYW75NSSx-dEb_EHqu8Ysw/edit#gid=0',
        'https://docs.google.com/spreadsheets/d/1XCtbHzP15FRduJzf_ena4tdye6oHwzpD-IRNdPV9jpM/edit#gid=0',
        'https://docs.google.com/spreadsheets/d/1EoAgbDBVdJIXVDMwy5wEmiEpAFDMuoy3p0qOVf5QDtQ/edit#gid=0',
    ]
    # sheet_name_core = 'image'

    # step 1:observe
    sheet_info = sheet_type.MP4_SHEET_NAME
    # df = process_image(urls=urls, sheet_info=sheet_info)
    df = process_mp3_mp4(sheet_info=sheet_info, urls=urls)

    # step2: crawl
    # crawl_image_datalake(df=df, sheet_info=sheet_info, object_type=sheet_info['object_type'])
    crawl_mp3_mp4(df=df, sheet_info=sheet_info)

    # step 3: check
    # checking_crawlingtask_image_crawler_status(df=df)
    # checking_crawlingtask_mp3_mp4_crawler_status(df=df)

    print("\n --- total time to process %s seconds ---" % (time.time() - start_time))
