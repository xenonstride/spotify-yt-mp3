import sys,requests,json,os
from os import path
from pytube import YouTube
from glob import iglob
from moviepy.editor import *
import eyed3
from apiclient.discovery import build

prev_dir = os.getcwd()
os.chdir(r"DIR") #replace with your music directory
if path.exists('art.png'):
    os.remove('art.png')

SP_CLIENT_ID = "XXXXXXXXXXXXXXXXXXXXX" #replace with your spotify client id
SP_CLIENT_SECRET = "XXXXXXXXXXXXXXXXXXXX" #replace with your spotify secret

AUTH_URL = 'https://accounts.spotify.com/api/token'

auth_response = requests.post(AUTH_URL,{
    'grant_type' : 'client_credentials',
    'client_id' : SP_CLIENT_ID,
    'client_secret' : SP_CLIENT_SECRET}
)

auth_response_data = auth_response.json()
access_token = auth_response_data['access_token']

headers = {
    'Authorization' : 'Bearer {token}'.format(token=access_token)
}

print("Enter album name : ",end='')
album_name=str(input())

Sp_BASE_URL = 'https://api.spotify.com/v1/'
album_name_api_req = album_name.replace(" ","%20")
query1 = 'search?q=album:'+album_name_api_req+'&type=album'
spotify_a1 = requests.get(Sp_BASE_URL+query1,headers=headers)
spotify_a2 = spotify_a1.json()
try:
    album_id = spotify_a2['albums']['items'][0]['id']
except IndexError:
    print("Album not found on Spotify")
    print("Exiting...")
    sys.exit()
query2 = 'albums/'+album_id
spotify_b1 = requests.get(Sp_BASE_URL+query2,headers=headers)
spotify_b2 = spotify_b1.json()

track_list = []
no_of_tracks = int(spotify_b2['total_tracks'])
print("Track list : ")
for i in range(no_of_tracks):
    track_list.append(spotify_b2['tracks']['items'][i]['name'])
    print(f"{i+1}) "+track_list[i])

print("\nEnter track numbers to download (separate by comma(,)) or press Enter to download all songs")
print("-->> ",end='')
requested_str = str(input())
requested_tracks_index = []
if requested_str=='':
    for i in range(no_of_tracks):
        requested_tracks_index.append(i)
else:
    for i in range(0,len(requested_str)+1,2):
        requested_tracks_index.append(int(requested_str[i])-1)

requested_tracks_ids = []
requested_tracks = []
for i in range(len(requested_tracks_index)):
    requested_tracks_ids.append(spotify_b2['tracks']['items'][requested_tracks_index[i]]['id'])
    requested_tracks.append(spotify_b2['tracks']['items'][requested_tracks_index[i]]['name'])

album_name = spotify_b2['name'].replace(' (Original Motion Picture Soundtrack)','') if ' (Original Motion Picture Soundtrack)' in spotify_b2['name'] else spotify_b2['name']

#ALBUM ART DOWNLOAD
r = requests.get(spotify_b2['images'][1]['url'])
with open("art.png",'wb') as f:
    f.write(r.content)

# SONG.LINK API SEGMENT
YT_LINKS = []
remove = []
for i in range(len(requested_tracks_index)):
    songlink_response = requests.get('https://api.song.link/v1-alpha.1/links?url=spotify%3Atrack%3A'+requested_tracks_ids[i]+'&userCountry=IN')
    links_json = songlink_response.json()
    try:
        YT_LINKS.append(links_json['linksByPlatform']['youtube']['url'])
    except KeyError:
        print(f"{requested_tracks[i]} is not found on API database")
        print("Search on youtube(y) or skip(n) : ",end='')
        choice = input()
        if choice=='y':
            YT_DEVELOPER_KEY = "XXXXXXXXXXXXXXXXXXXXXXXX"  #replace with your YouTube developer key
            YOUTUBE_API_SERVICE_NAME = "youtube"
            YOUTUBE_API_VERSION = "v3"
            youtube_object = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,developerKey = YT_DEVELOPER_KEY)
            def youtube_search_keyword(query, max_results):
                search_keyword = youtube_object.search().list(q = query, part = "id, snippet",
                                                           maxResults = max_results).execute()
                results = search_keyword.get("items", [])
                return results
            results = youtube_search_keyword(requested_tracks[i]+' '+album_name+' movie audio song',1)
            video_id = results[0]['id']['videoId']
            YT_BASE_URL = 'https://www.youtube.com/watch?v='
            YT_LINKS.append(YT_BASE_URL+video_id)
        else:
            print(f"Skipping {requested_tracks[i]}")
            remove.append(i)
k=0
for i in range(len(remove)):
    requested_tracks_index.pop(remove[i]+k)
    requested_tracks.pop(remove[i]+k)
    k-=1

# DOWNLOAD,RENAME,CONVERT,ADD METADATA
print('')
video_objs = []
for i in range(len(requested_tracks_index)):
    #DOWNLOAD
    video_objs.append(YouTube(YT_LINKS[i]))
    print(f"Downloading {i+1}/{len(requested_tracks_index)} - {requested_tracks[i]} ",end='')
    video_objs[i].streams.first().download()
    print(" -> Downloaded")
    #RENAME
    files = sorted(iglob(os.path.join(os.getcwd(),'*')),key=os.path.getctime,reverse=True)
    old_title = files[0].replace(os.getcwd()+'/','')
    new_title = requested_tracks[i]+ f' [{album_name}]'
    os.rename(old_title,new_title+'.mp4')
    #CONVERT
    print("   [*] Converting to mp3")
    video = VideoFileClip(os.getcwd()+'\\'+new_title+'.mp4')
    audio = video.audio
    audio.write_audiofile(os.getcwd()+'\\'+new_title+'.mp3',logger=None)
    audio.close()
    video.close()
    os.remove(os.getcwd()+'\\'+new_title+'.mp4')
    #ADD METADATA
    print("   [*] Adding metadata")
    mp3 = eyed3.load(os.getcwd()+'\\'+new_title+'.mp3')
    if (mp3.tag == None):
        mp3.initTag()
    mp3.tag.title = requested_tracks[i]
    mp3.tag.album = album_name
    mp3.tag.images.set(3, open("art.png", 'rb').read(), 'image/png')
    mp3.tag.save(version=eyed3.id3.ID3_V2_3)

#Completed
os.remove("art.png")
os.chdir(prev_dir)
if len(video_objs)==len(requested_tracks_index):
    print("\nSuccessfully downloaded all songs")
else:
    print("Something wrong")