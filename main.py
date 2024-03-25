#Gets the user tracks

from flask import Flask, redirect, request, jsonify, session
from datetime import datetime
import requests
from pymongo import MongoClient

import urllib.parse
import json

import os
from dotenv import dotenv_values

#http://localhost:5000
app = Flask(__name__)
app.secret_key = "Garbage"

#API Client Info, URIs, environment variables
script_directory = os.path.dirname(os.path.abspath(__file__))   #directory path
env_id_file_path = os.path.join(script_directory, '.env.id')        #client id env file
env_secret_file_path = os.path.join(script_directory,'.env.secret') #secret env file
#env_mongo_path = os.path.join(script_directory, '.env.mongo')

config = {
    **dotenv_values(env_id_file_path),
    **dotenv_values(env_secret_file_path),
#    **dotenv_values(env_mongo_path)
}

app.secret_key = config['SECRET_KEY']
client_id = config['CLIENT_ID']
client_secret = config['CLIENT_SECRET']

redirect_uri = 'http://localhost:5000/callback'
AUTH_URL = 'https://accounts.spotify.com/authorize'
token_url = 'https://accounts.spotify.com/api/token'
API_base_url = 'https://api.spotify.com/v1/'

#MongoDB Info
client = MongoClient("mongodb://127.0.0.1:27017/mongosh?directConnection=true&serverSelectionTimeoutMS=2000")
database = client.SpotifyInfo

# names = [
#     {"name" : "Shrek", "spotifyid" : "onion"},
#     {"name" : "Michael", "spotifyid" : "Kaiser"},
#     {"name" : "Obama", "spotifyid" : "9/11"}
# ]
# database.Users.insert_many(names)

# for user in database.Users.find():
#     print(user)

# database.Users.delete_many({"name" : {"$ne" : "Michael"}})


#Login page
@app.route('/')
def index():
    return "Welcome: <a href='/login'>Login with Spotify</a>"   #This is the button to login where we redirect to them our endpoint

@app.route('/login')
def login():
    scope = 'user-read-private user-read-email playlist-read-private playlist-read-collaborative user-library-read user-top-read' 
    params = {
        'client_id' : client_id,
        'response_type' : 'code',
        'scope' : scope,
        'redirect_uri': redirect_uri,
        'show_dialog': True             #NEED THIS TO LOG IN
    }
    
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
    return redirect(auth_url)
    
    
#Permission/Token Retrival
@app.route('/callback')
def callback():
    #Check for error
    if 'error' in request.args:
        return jsonify({'error': request.args['error']})
    
    if 'code' in request.args:
        
        data = {
            'code' : request.args['code'],       #This is the code they sent us
            'grant_type': 'authorization_code',  
            'redirect_uri': redirect_uri,        #Dont use this
            'client_id': client_id,
            'client_secret': client_secret             
        }
        
        response = requests.post(url=token_url, data=data)
        token_info = response.json() #Comes as json object
        
        if 'error' in token_info:
            return jsonify({'error': token_info['error']})
        
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info['refresh_token']
        session['expires_at'] = datetime.now().timestamp() + token_info['expires_in']     #Lasts one hour. Just get the time and add the time it expires.
        
        return redirect('/tracks')    

#Track/Songs/Artist Retrival
@app.route('/tracks')
def get_tracks():
    headers = {
        'Authorization': f"Bearer {session['access_token']}"
    }
    
    #response stores result of endpoint    
    # response = requests.get(API_base_url + 'me/playlists', headers=headers)

    # try:
    #     playlists_json = response.json()
    #     all_playlists = playlists_json['items']
    # except json.JSONDecodeError as e:
    #     print("JSON decoding error:", str(e))
    #     return jsonify({"error": f"{response.content} Code:{response.status_code}"})
            
    # All_Songs = []
    
    # for playlist in all_playlists:
    #     playlist_id = playlist['id']       #gets id from playlist i
    #     total_tracks = playlist['tracks']['total']
        
    #     offset = 0
        
    #     while offset < total_tracks:        #limit is 100 for each retrieval
    #         params = {'offset':offset, 'limit': 100}
    #         tracks_data_json = requests.get(API_base_url + f'playlists/{playlist_id}/tracks', headers=headers, params=params)
    #         tracks_data = tracks_data_json.json()
            
    #         for j in tracks_data['items']:
    #             if isinstance(j, dict) and 'track' in j and isinstance(j['track'], dict):   #is j a dictionary, is the track in in, is the track a dictionary.
    #                 track_name = j['track']['name']
    #                 All_Songs.append(track_name)
           
    #         offset += 100
    #Put Items in database saved under this user
    #Display top 20-30 tracks of user with info about tracks
    
    response = requests.get(API_base_url + 'me/top/tracks', headers=headers)
    
    try:
        top_tracks_json = response.json()
        top_tracks = top_tracks_json['items']
    except json.JSONDecodeError as e:
        print("JSON decoding error:", str(e))
        return jsonify({"error": f"{response.content} Code:{response.status_code}"})
    
    Top_Tracks = []
    
    for tracks in top_tracks:
        Top_Tracks.append(f"{tracks['name']}, {tracks['popularity']}")
        
    return Top_Tracks
#popularity field measures how popular an item is on spotify. Could be cool to rank your favorites based on most popular on Spotify.

#Refresh Token
@app.route('/refresh_token')
def refresh_token():
    if 'refresh_token' not in session:
        return redirect('/login')

    #refresh token if it expired
    if datetime.now().timestamp() > session['expires_at']:    
        request_body = {
            'grant_type' : 'refresh_token',
            'refresh_token' : session['refresh_token'],
            'client_id' : client_id,
            'client_secret' : client_secret
        }    
        
        response = requests.post(token_url, data=request_body)
        new_token_info = response.json()
        
        session['access_token'] = new_token_info['access_token']
        session['expires_at'] = datetime.now().timestamp() + new_token_info['expires_in']
        
        return redirect('/tracks') 

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    