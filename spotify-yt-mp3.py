import sys
import threading
import requests
import json
import os
from os import path
from pytube import YouTube
from glob import iglob
from moviepy.editor import *
import eyed3
from apiclient.discovery import build
import shutil

#GET API KEYS FROM secret.json file
with open("my_secret.json", 'r') as f:
    data = json.load(f)
    SP_CLIENT_ID = data["client_id"]
    SP_CLIENT_SECRET = data["client_secret"]

#SPOTIFY API AUTHENTICATION
AUTH_URL = 'https://accounts.spotify.com/api/token'
auth_response = requests.post(AUTH_URL, {
    'grant_type': 'client_credentials',
    'client_id': SP_CLIENT_ID,
    'client_secret': SP_CLIENT_SECRET}
)
auth_response_data = auth_response.json()
access_token = auth_response_data['access_token']
headers = {
    'Authorization': f'Bearer {access_token}'
}

#INVALID CHARACTERS FOR FILE NAMES
invalid_chars=['\\','/',':','*','?','"','<','>','|','%',"'",'.']

#DOWNLOADER FUNCTION FOR MULTITHREADING
def downloader(link, track_number, requested_tracks, requested_tracks_artists, album_name):

    #FILE NAME
    new_title = requested_tracks[track_number] + f' [{album_name}]'
    for i in invalid_chars:
        if i in new_title:
            new_title=new_title.replace(i,'')

    #DOWNLOAD FILE
    YouTube(link).streams.first().download(filename=new_title)
    
    # CONVERT MP4 TO MP3
    video = VideoFileClip(os.getcwd()+'\\'+new_title+'.mp4')
    audio = video.audio
    audio.write_audiofile(os.getcwd()+'\\'+new_title+'.mp3', logger=None)
    audio.close()
    video.close()
    
    #DELETE MP4 FILE
    os.remove(os.getcwd()+'\\'+new_title+'.mp4')

    # ADD METADATA
    mp3 = eyed3.load(os.getcwd()+'\\'+new_title+'.mp3')
    if (mp3.tag == None):
        mp3.initTag()
    mp3.tag.title = requested_tracks[track_number]
    mp3.tag.album = album_name
    mp3.tag.artist = requested_tracks_artists[track_number]
    mp3.tag.images.set(3, open(f"art{track_number}.png", 'rb').read(), 'image/png')
    mp3.tag.save(version=eyed3.id3.ID3_V2_3)


def main(album_name):

    # REPLACE WITH YOUR MUSIC DIRECTORY
    os.chdir(r"C:\Users\hsrip\Music\My-Music")

    # DOWNLOAD ALBUM ART
    if path.exists('art.png'):
        os.remove('art.png')

    # SEARCH SPOTIFY FOR GIVEN ALBUM
    Sp_BASE_URL = 'https://api.spotify.com/v1/'
    album_name_api_req = album_name.replace(" ", "%20")
    query1 = 'search?q=album:'+album_name_api_req+'&type=album'
    spotify_a1 = requests.get(Sp_BASE_URL+query1, headers=headers)
    spotify_a2 = spotify_a1.json()

    #GET ALBUM ID IF FOUND
    try:
        album_id = spotify_a2['albums']['items'][0]['id']
    #IF ALBUM NOT FOUND
    except IndexError:
        print("Album not found on Spotify")
        return

    # GET TRACKS OF ALBUM FROM TOP SEARCH RESULT IN SPOTIFY
    query2 = 'albums/'+album_id
    spotify_b1 = requests.get(Sp_BASE_URL+query2, headers=headers)
    spotify_b2 = spotify_b1.json()

    track_list = []
    no_of_tracks = int(spotify_b2['total_tracks'])
    print("Tracks list : ")
    for i in range(no_of_tracks):
        track_list.append(spotify_b2['tracks']['items'][i]['name'])
        print(f"{i+1}) "+track_list[i])

    album_name = spotify_b2['name'].replace(' (Original Motion Picture Soundtrack)',
                                            '') if ' (Original Motion Picture Soundtrack)' in spotify_b2['name'] else spotify_b2['name']

    print("\nEnter track numbers to download (separate by comma(,)) or press Enter to download all songs or no to search again")
    print("-->> ", end='')
    requested_str = str(input())
    requested_tracks_index = []

    #IF WRONG ALBUM FOUND
    if requested_str == 'no':
        return
    #DOWNLOAD ALL SONGS
    elif requested_str == '':
        requested_tracks_index = [i for i in range(no_of_tracks)]
    #DOWNLOAD ONLY REQUESTED SONGS
    else:
        requested_tracks_index = requested_str.split(',')
        requested_tracks_index = [int(a)-1 for a in requested_tracks_index]

    requested_tracks_ids = []
    requested_tracks = []
    requested_tracks_artists = []
    for i in range(len(requested_tracks_index)):
        requested_tracks_ids.append(
            spotify_b2['tracks']['items'][requested_tracks_index[i]]['id'])
        requested_tracks.append(
            spotify_b2['tracks']['items'][requested_tracks_index[i]]['name'])
        requested_tracks_artists.append(
            spotify_b2['tracks']['items'][requested_tracks_index[i]]['artists'][0]['name'])


    # ALBUM ART DOWNLOAD
    r = requests.get(spotify_b2['images'][1]['url'])
    with open("art.png", 'wb') as f:
        f.write(r.content)
    
    #CREATE ALBUM ART COPIES FOR EACH THREAD
    os.rename("art.png","art0.png")
    for i in range(len(requested_tracks)-1):
        shutil.copyfile("art0.png",f"art{i+1}.png")

    # SONG.LINK API SEGMENT
    YT_LINKS = []
    remove = []
    for i in range(len(requested_tracks_index)):
        songlink_response = requests.get(
            'https://api.song.link/v1-alpha.1/links?url=spotify%3Atrack%3A'+requested_tracks_ids[i]+'&userCountry=IN')
        links_json = songlink_response.json()
        try:
            YT_LINKS.append(links_json['linksByPlatform']['youtube']['url'])
        except KeyError:
            print(f"{requested_tracks[i]} is not found on API database")
            print("Search on youtube(y) or skip(n) : ", end='')
            choice = input()
            if choice == 'y':
                # replace with your YouTube developer key
                YT_DEVELOPER_KEY = "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                YOUTUBE_API_SERVICE_NAME = "youtube"
                YOUTUBE_API_VERSION = "v3"
                youtube_object = build(
                    YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=YT_DEVELOPER_KEY)

                def youtube_search_keyword(query, max_results):
                    search_keyword = youtube_object.search().list(q=query, part="id, snippet",
                                                                  maxResults=max_results).execute()
                    results = search_keyword.get("items", [])
                    return results
                results = youtube_search_keyword(
                    requested_tracks[i]+' '+album_name+' movie audio song', 1)
                video_id = results[0]['id']['videoId']
                YT_BASE_URL = 'https://www.youtube.com/watch?v='
                YT_LINKS.append(YT_BASE_URL+video_id)
            else:
                print(f"Skipping {requested_tracks[i]}")
                remove.append(i)
    k = 0
    for i in range(len(remove)):
        requested_tracks_index.pop(remove[i]+k)
        requested_tracks.pop(remove[i]+k)
        requested_tracks_artists.pop(remove[i]+k)
        k -= 1

    # DOWNLOAD,RENAME,CONVERT,ADD METADATA
    print('')
    video_links = YT_LINKS
    print(f"Downloading {len(requested_tracks)} songs")
    threads=[]
    
    for i in range(len(requested_tracks_index)):
        # CREATE THREADS
        threadObj=threading.Thread(target=downloader,args=[video_links[i],i,requested_tracks,requested_tracks_artists,album_name])
        threads.append(threadObj)
    
    #STARTS THREADS
    [t.start() for t in threads]
    [t.join() for t in threads]

    #DELETE ALBUM ART FILES
    for i in range(len(requested_tracks)):
        os.remove(f"art{i}.png")

    if len(video_links) == len(requested_tracks_index):
        print("\nSuccessfully downloaded all songs")
    else:
        print("Something wrong")
        sys.exit()

while(True):
    print("Enter album name ('z' to stop) : ", end='')
    album_name = str(input())
    if album_name != 'z':
        main(album_name)
    else:
        sys.exit()

# Completed
