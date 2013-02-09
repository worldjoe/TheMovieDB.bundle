# TheMovieDB
# Multi-language support added by Aqntbghd
# 3.0 API update by ToMM

# TODO : Use proper country code for content-rating (hard coded to US right now)

import time

# apiary.io debugging URL
# BASE_URL = 'http://private-ad99a-themoviedb.apiary.io/3/'

BASE_URL = 'http://api.themoviedb.org/3/'

TMDB_CONFIG_URL = BASE_URL + 'configuration?api_key=a3dc111e66105f6387e99393813ae4d5'
TMDB_ID_URL = BASE_URL + 'movie/%s?api_key=a3dc111e66105f6387e99393813ae4d5&language=%s'
TMDB_MOVIE_URL = BASE_URL + 'movie/%s?api_key=a3dc111e66105f6387e99393813ae4d5&append_to_response=releases,casts,images&language=%s'

def Start():
  HTTP.CacheTime = CACHE_1HOUR * 4
  HTTP.Headers['Accept'] = 'application/json'

class TMDbAgent(Agent.Movies):
  name = 'TheMovieDB'
  languages = [Locale.Language.English, Locale.Language.Swedish, Locale.Language.French,
               Locale.Language.Spanish, Locale.Language.Dutch, Locale.Language.German,
               Locale.Language.Italian, Locale.Language.Danish]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']

  def search(self, results, media, lang):
    if media.primary_metadata is not None:
      tmdb_id = str(JSON.ObjectFromURL(TMDB_ID_URL % (media.primary_metadata.id, lang))['id'])
      if tmdb_id:
        results.Append(MetadataSearchResult(id = tmdb_id, score = 100))

  def update(self, metadata, media, lang): 
    proxy = Proxy.Preview
    
    # try n times waiting 5 seconds in between if something goes wrong
    tmdb_dict = None
    for t in range(3):
      try:
        tmdb_dict = JSON.ObjectFromURL(TMDB_MOVIE_URL % (metadata.id, lang))
      except:
        time.sleep(5)
      if isinstance(tmdb_dict, dict):
        break

    if tmdb_dict is None or not isinstance(tmdb_dict, dict):
      Log('Exception fetching JSON from theMovieDB (1).')
      return None

    # Rating.
    votes = tmdb_dict['vote_count']
    rating = tmdb_dict['vote_average']
    if votes > 3:
      metadata.rating = rating

    # Title of the film.
    if Prefs['title']:
      metadata.title = tmdb_dict['title']
    else:
      metadata.title = ""

    # Tagline.
    metadata.tagline = tmdb_dict['tagline']

    # Content rating.
    for country in tmdb_dict['releases']['countries']:
      if country['iso_3166_1'] == 'US':
        metadata.content_rating = country['certification']    
    
    # Summary.
    metadata.summary = tmdb_dict['overview']
    if metadata.summary == 'No overview found.':
      metadata.summary = ""

    # Release date.
    try: 
      metadata.originally_available_at = Datetime.ParseDate(tmdb_dict['release_date']).date()
      metadata.year = metadata.originally_available_at.year
    except: 
      pass

    # Runtime.
    try: metadata.duration = int(tmdb_dict['runtime']) * 60 * 1000
    except: pass

    # Genres.
    metadata.genres.clear()
    for genre in tmdb_dict['genres']:
      metadata.genres.add(genre['name'])

    # Collections.
    metadata.collections.clear()
    if Prefs['collections'] and tmdb_dict['belongs_to_collection'] is not None:
      metadata.collections.add(tmdb_dict['belongs_to_collection']['name'].replace(' Collection',''))

    # Studio.
    try: metadata.studio = tmdb_dict['production_companies'][0]['name'].strip()
    except: pass

    # Cast.
    metadata.directors.clear()
    metadata.writers.clear()
    metadata.roles.clear()
    config_dict = JSON.ObjectFromURL(TMDB_CONFIG_URL, cacheTime=CACHE_1MONTH * 3)

    for member in tmdb_dict['casts']['crew']:
      if member['job'] == 'Director':
        metadata.directors.add(member['name'])
      elif member['job'] == 'Writing':
        metadata.writers.add(member['name'])
    
    for member in tmdb_dict['casts']['cast']:
        role = metadata.roles.new()
        role.role = member['character']
        role.actor = member['name']
        if member['profile_path'] is not None:
          role.photo = config_dict['images']['base_url'] + 'original' + member['profile_path']

    valid_names = list()
    for i, poster in enumerate(sorted(tmdb_dict['images']['posters'], key=lambda k: k['vote_count'], reverse=True)):
      poster_url = config_dict['images']['base_url'] + 'original' + poster['file_path']
      thumb_url = config_dict['images']['base_url'] + 'w500' + poster['file_path']
      valid_names.append(poster_url)

      if poster_url not in metadata.posters:
        try: metadata.posters[poster_url] = proxy(HTTP.Request(thumb_url), sort_order = i)
        except: pass

    metadata.posters.validate_keys(valid_names)
  
    valid_names = list()
    for i, backdrop in enumerate(sorted(tmdb_dict['images']['backdrops'], key=lambda k: k['vote_count'], reverse=True)):
      backdrop_url = config_dict['images']['base_url'] + 'original' + backdrop['file_path']
      thumb_url = config_dict['images']['base_url'] + 'w780' + backdrop['file_path']
      valid_names.append(backdrop_url)

      if backdrop_url not in metadata.art:
        try: metadata.art[backdrop_url] = proxy(HTTP.Request(thumb_url), sort_order = i)
        except: pass

    metadata.art.validate_keys(valid_names)