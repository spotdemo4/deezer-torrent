import subprocess
import deezer
import musicbrainzngs
import os
import random
import requests
from torf import Torrent
from qbittorrent import Client
from dotenv import load_dotenv
load_dotenv()

# Musicbrainz search
musicbrainzngs.set_useragent(
    "Deezertorrent app",
    "0.1",
    "https://trev.xyz"
)
release_count = musicbrainzngs.search_releases(primarytype='Album,Single,EP', status='official', format='Digital Media', limit=1)['release-count']

def get_random_release():
    try:
        return random.choice(musicbrainzngs.search_releases(primarytype='Album,Single,EP', status='official', format='Digital Media', limit=5, offset=random.randint(0, release_count))['release-list'])
    except IndexError:
        return get_random_release()

print('Finding random release...')
release = get_random_release()
print(f'{release["artist-credit"][0]["artist"]["name"]} - {release["title"]} [{release.get("date", "????").split("-")[0]} {release["release-group"]["primary-type"]}]')

# Deezer search
print()
if os.getenv('DEEZER_ACCESS_TOKEN'):
    deezer_client = deezer.Client(access_token=os.getenv('DEEZER_ACCESS_TOKEN'))
    print('Deezer search... ', end='', flush=True)
    deezer_search = deezer_client.search_albums(query=f'artist:"{release["artist-credit"][0]["artist"]["name"]}" album:"{release["title"]}"', strict=True)
    if len(deezer_search) == 0:
        print('Not found')
        exit()
    elif len(deezer_search) == 1:
        print('Found ✓')
        deezer_album = deezer_search[0]
    else:
        print(f'Found {len(deezer_search)} results')
        for i, album in enumerate(deezer_search):
            print(f'- [{i+1}] {album.artist.name} - {album.title} [{album.release_date.year} {album.record_type.capitalize()}]')
        index = int(input('Select release: ')) - 1
        deezer_album = deezer_search[index]
else:
    print('Deezer not configured')
    exit()

# Orpheus search
print()
if os.getenv('ORPHEUS_API_KEY'):
    print('Orpheus search... ', end='', flush=True)
    orpheus_search = requests.get(f'https://orpheus.network/ajax.php?action=browse&searchstr={deezer_album.title}&artistname={deezer_album.artist.name}', headers={'Authorization': 'token ' + os.getenv('ORPHEUS_API_KEY')}).json()
    if orpheus_search['status'] != 'success':
        print('Error: ' + orpheus_search['status'])
        exit()
    elif len(orpheus_search['response']['results']) > 0:
        print('Found ✗')
        for album in orpheus_search['response']['results']:
            print(f'- {album["artist"]} - {album["groupName"]} [{album["groupYear"]} {album["releaseType"].capitalize()}]')
        abort = input('Abort? [Y/n] ')
        if abort != 'n' and abort != 'N':
            exit()
    else:
        print('Not found ✓')
else:
    print('Orpheus API not configured')

# Download
print()
print("Downloading...")
subprocess.run(["python", "orpheus.py", "--output", "../download/", deezer_album.link], cwd="orpheusdl/")

# Create Orpheus torrent
print()
if os.getenv('ORPHEUS_ANNOUNCE_URL'):
    print("Creating Orpheus torrent...")
    torrent = Torrent(path=f'./download/{deezer_album.artist.name} - {deezer_album.title} ({deezer_album.release_date.year}) [WEB] [FLAC]/',
                    trackers=[os.getenv('ORPHEUS_ANNOUNCE_URL')],
                    source='OPS',
                    private=True)
    torrent.generate()
    torrent.write(f'./torrents/[Orpheus] {deezer_album.artist.name} - {deezer_album.title} ({deezer_album.release_date.year}) [WEB] [FLAC].torrent')
else:
    print("Orpheus tracker not configured")

# Upload to imgur
print()
if os.getenv("IMGUR_CLIENT_ID"):
    print("Uploading image...")
    imgur_response = requests.post('https://api.imgur.com/3/image', data={'image': deezer_album.cover_xl, 'type': 'url'}, headers={'Authorization': f'Client-ID {os.getenv("IMGUR_CLIENT_ID")}'}).json()
    print(imgur_response['data']['link'])
else:
    print("Imgur not configured")

# Get metadata
print()
if os.getenv("YADG_API_KEY"):
    print("Getting metadata...")
    yadg_query = requests.post('https://yadg.cc/api/v2/query/', data={'input': deezer_album.link}, headers={'Authorization': f'Token {os.getenv("YADG_API_KEY")}', 'Accept': 'application/json'}).json()
    print(f'https://yadg.cc/result/{yadg_query["resultId"]}')
else:
    print("YADG not configured")

print()
print("---- Results ----")
print(f"Release type: {deezer_album.record_type.capitalize()}")
if os.getenv("IMGUR_CLIENT_ID"):
    print(f"Image: {imgur_response['data']['link']}")
print(f"Artist: {deezer_album.artist.name}")
print(f"Contributing artists: {', '.join([artist.name for artist in deezer_album.contributors])}")
print(f"Album title: {deezer_album.title}")
print(f"Year: {deezer_album.release_date.year}")
print(f"Label: {deezer_album.label}")
print(f"Tags: {', '.join([genre.name for genre in deezer_album.genres])}")
print(f"Album description: https://yadg.cc/result/{yadg_query['resultId']}")

# Upload to qBittorrent
print()
upload = input('Upload to qBittorrent? [Y/n] ')
if upload != 'n' and upload != 'N' and os.getenv('QBIT_HOST') and os.getenv('QBIT_USER') and os.getenv('QBIT_PASS'):
    print("Uploading to qBittorrent...")
    qb = Client(os.getenv('QBIT_HOST'))
    qb.login(os.getenv('QBIT_USER'), os.getenv('QBIT_PASS'))
    qb.download_from_file(f'./torrents/[Orpheus] {deezer_album.artist.name} - {deezer_album.title} ({deezer_album.release_date.year}) [WEB] [FLAC].torrent')