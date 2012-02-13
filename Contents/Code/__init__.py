# TheMovieDB
# Multi-language support added by Aqntbghd

# TODO : Deal with languages AND locations as TMDB makes the difference between them.
# TODO : Deal with TMDB set of films as collections as soon as the API is made public

import time

TMDB_GETINFO_IMDB = 'http://api.themoviedb.org/2.1/Movie.imdbLookup/en/json/a3dc111e66105f6387e99393813ae4d5/%s'
TMDB_GETINFO_TMDB = 'http://api.themoviedb.org/2.1/Movie.getInfo/%s/json/a3dc111e66105f6387e99393813ae4d5/%s'
TMDB_GETINFO_HASH = 'http://api.themoviedb.org/2.1/Hash.getInfo/%s/json/a3dc111e66105f6387e99393813ae4d5/%s'

TMDB_LANGUAGE_CODES = {
  'en': 'en',
  'sv': 'sv',
  'fr': 'fr-FR',
  'es': 'es',
  'nl': 'nl',
  'de': 'de',
  'it': 'it',
  'da': 'da'
}

#v3
TMDB_BASEURL            = 'http://api.themoviedb.org/3/'
TMDB_API_KEY            = '?api_key=a3dc111e66105f6387e99393813ae4d5'
TMDB_LANGUAGE           = '&language=%s'

TMDB_GETCONFIG          = TMDB_BASEURL + 'configuration' + TMDB_API_KEY
TMDB_MOVIE_INFO         = TMDB_BASEURL + 'movie/%s' + TMDB_API_KEY + TMDB_LANGUAGE
TMDB_MOVIE_IMAGES       = TMDB_BASEURL + 'movie/%s/images' + TMDB_API_KEY
TMDB_MOVIE_IMAGES_LANG  = TMDB_BASEURL + 'movie/%s/images' + TMDB_API_KEY + TMDB_LANGUAGE
TMDB_MOVIE_CASTS        = TMDB_BASEURL + 'movie/%s/casts' + TMDB_API_KEY
TMDB_MOVIE_TRAILERS     = TMDB_BASEURL + 'movie/%s/trailers' + TMDB_API_KEY + TMDB_LANGUAGE
TMDB_MOVIE_RELEASES     = TMDB_BASEURL + 'movie/%s/releases' + TMDB_API_KEY
TMDB_MOVIE_ALTTITLE     = TMDB_BASEURL + 'movie/%s/alternative_titles' + TMDB_API_KEY + '&country=%s'


def Start():
  HTTP.CacheTime = CACHE_1HOUR * 4

def GetLanguageCode(lang):
  if TMDB_LANGUAGE_CODES.has_key(lang):
    return TMDB_LANGUAGE_CODES[lang]
  else:
    return 'en'

@expose
def GetImdbIdFromHash(openSubtitlesHash, lang):
  try:
    tmdb_dict = JSON.ObjectFromURL(TMDB_GETINFO_HASH % (GetLanguageCode(lang), str(openSubtitlesHash)))[0]
    if isinstance(tmdb_dict, dict) and tmdb_dict.has_key('imdb_id'):
      return MetadataSearchResult(
        id    = tmdb_dict['imdb_id'],
        name  = tmdb_dict['name'],
        year  = None,
        lang  = lang,
        score = 94)
    else:
      return None

  except:
    return None

class TMDbAgent(Agent.Movies):
  name = 'TheMovieDB'
  languages = [Locale.Language.English, Locale.Language.Swedish, Locale.Language.French,
               Locale.Language.Spanish, Locale.Language.Dutch, Locale.Language.German,
               Locale.Language.Italian, Locale.Language.Danish]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']

  def search(self, results, media, lang):
    if media.primary_metadata is not None:
      if media.primary_metadata.id:
        results.Append(MetadataSearchResult(id = media.primary_metadata.id, score = 100))
    #elif media.openSubtitlesHash is not None:
    #  match = GetImdbIdFromHash(media.openSubtitlesHash, lang)

  def update(self, metadata, media, lang): 
    proxy = Proxy.Preview
    #try:
    HTTP.Headers['Accept'] = 'application/json'
    config_dict = JSON.ObjectFromURL(TMDB_GETCONFIG, cacheTime=600000)
    tmdb_image_baseurl = config_dict['images']['base_url']
    
    tmdb_dict = JSON.ObjectFromURL(TMDB_MOVIE_INFO % (metadata.id, GetLanguageCode(lang)))
    #Log(tmdb_info)
    #if tmdb_info.count('503 Service Unavailable') > 0:
    #  time.sleep(5)
    #  tmdb_info = HTTP.Request(TMDB_MOVIE_INFO % (metadata.id, GetLanguageCode(lang)), cacheTime=0).content
    #Log(tmdb_dict)
    #except:
    #  Log('Exception fetching JSON from theMovieDB (1).')
    #  return None
    
    # Rating.
    if tmdb_dict['vote_count'] > 3:
      metadata.rating = tmdb_dict['vote_average']

    # Title of the film.
    if Prefs['title']:
      metadata.title = tmdb_dict['original_title']
    else:
      metadata.title = ''

    # Tagline.
    metadata.tagline = tmdb_dict['tagline']

    # Content rating.
    release_dict = JSON.ObjectFromURL(TMDB_MOVIE_RELEASES % metadata.id)
    metadata.content_rating = release_dict['countries'][0]['certification']

    # Summary.
    metadata.summary = tmdb_dict['overview']
    if metadata.summary == 'No overview found.':
      metadata.summary = ''

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

    # Studio.
    try: metadata.studio = tmdb_dict['production_companies'][0]['name']
    except: pass

    # Cast.
    cast_dict = JSON.ObjectFromURL(TMDB_MOVIE_CASTS % metadata.id)
    metadata.directors.clear()
    metadata.writers.clear()
    metadata.roles.clear()

    for member in cast_dict['cast']:
      role = metadata.roles.new()
      role.role = member['character']
      role.actor = member['name']
    for member in cast_dict['crew']:        
      if member['job'] == 'Director':
        metadata.directors.add(member['name'])
      elif member['job'] == 'Author':
        metadata.writers.add(member['name'])

    #images
    images_dict = JSON.ObjectFromURL(TMDB_MOVIE_IMAGES % metadata.id) #, GetLanguageCode(lang)))
    #tmdb_image_baseurl
    i = 0 # for sort order
    valid_names = list()
    for p in images_dict['posters']:
      i += 1
      valid_names.append(p['file_path'])
      if p['file_path'] not in metadata.posters:
        try: metadata.posters[tmdb_image_baseurl + 'original' + p['file_path']] = proxy(tmdb_image_baseurl + 'w92' + p['file_path'], sort_order = i)
        except: pass
    metadata.posters.validate_keys(valid_names)
    
    valid_names = list()
    i = 0
    for b in images_dict['backdrops']:
      i += 1
      valid_names.append(b['file_path'])
      if b['file_path'] not in metadata.art:
        try: metadata.art[tmdb_image_baseurl + 'original' + b['file_path']] = proxy(tmdb_image_baseurl + 'w300' + b['file_path'], sort_order = i)
        except: pass
    metadata.art.validate_keys(valid_names)

  def get_tmdb_id(self, imdb_id):
    try:
      tmdb_info = HTTP.Request(TMDB_MOVIE_INFO % str(imdb_id)).content
      if tmdb_info.count('503 Service Unavailable') > 0:
        time.sleep(5)
        tmdb_info = HTTP.Request(TMDB_MOVIE_INFO % str(imdb_id), cacheTime=0).content
      tmdb_dict = JSON.ObjectFromString(tmdb_info)[0]
    except:
      Log('Exception fetching JSON from theMovieDB (2).')
      return None
    if tmdb_dict and isinstance(tmdb_dict, dict):
      return str(tmdb_dict['id'])
    else:
      return None
