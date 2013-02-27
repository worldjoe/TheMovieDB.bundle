# TheMovieDB
# Multi-language support added by Aqntbghd
# 3.0 API update by ToMM

import time

# apiary.io debugging URL
# BASE_URL = 'http://private-ad99a-themoviedb.apiary.io/3/'

BASE_URL = 'https://api.themoviedb.org/3/'

TMDB_CONFIG_URL = BASE_URL + 'configuration?api_key=a3dc111e66105f6387e99393813ae4d5'
TMDB_MOVIE_URL = BASE_URL + 'movie/%s?api_key=a3dc111e66105f6387e99393813ae4d5&append_to_response=releases,casts&language=%s'
TMDB_IMAGES_URL = BASE_URL + 'movie/%s/images?api_key=a3dc111e66105f6387e99393813ae4d5'
TMDB_SEARCH_URL = BASE_URL + 'search/movie?api_key=a3dc111e66105f6387e99393813ae4d5&query=%s&year=%s&language=%s&include_adult=true'

ARTWORK_ITEM_LIMIT = 15
REQUEST_RETRY_LIMIT = 3
VOTE_COUNT_BOOST = 100
RE_IMDB_ID = Regex('^tt\d{7}$')

TMDB_COUNTRY_CODE = {
  'Argentina': 'AR',
  'Australia': 'AU',
  'Austria': 'AT',
  'Belgium': 'BE',
  'Belize': 'BZ',
  'Bolivia': 'BO',
  'Brazil': 'BR',
  'Canada': 'CA',
  'Chile': 'CL',
  'Colombia': 'CO',
  'Costa Rica': 'CR',
  'Czech Republic': 'CZ',
  'Denmark': 'DK',
  'Dominican Republic': 'DO',
  'Ecuador': 'EC',
  'El Salvador': 'SV',
  'France': 'FR',
  'Germany': 'DE',
  'Guatemala': 'GT',
  'Honduras': 'HN',
  'Hong Kong SAR': 'HK',
  'Ireland': 'IE',
  'Italy': 'IT',
  'Jamaica': 'JM',
  'Liechtenstein': 'LI',
  'Luxembourg': 'LU',
  'Mexico': 'MX',
  'Netherlands': 'NL',
  'New Zealand': 'NZ',
  'Nicaragua': 'NI',
  'Panama': 'PA',
  'Paraguay': 'PY',
  'Peru': 'PE',
  'Portugal': 'PT',
  'Peoples Republic of China': 'CN',
  'Puerto Rico': 'PR',
  'Russia': 'RU',
  'Singapore': 'SG',
  'South Africa': 'ZA',
  'Spain': 'ES',
  'Sweden': 'SV',
  'Switzerland': 'CH',
  'Taiwan': 'TW',
  'Trinidad': 'TT',
  'United Kingdom': 'GB',
  'United States': 'US',
  'Uruguay': 'UY',
  'Venezuela': 'VE'
}

####################################################################################################
def Start():
  HTTP.Headers['Accept'] = 'application/json'

####################################################################################################
class TMDbAgent(Agent.Movies):
  name = 'TheMovieDB'
  languages = [Locale.Language.English, Locale.Language.Swedish, Locale.Language.French,
               Locale.Language.Spanish, Locale.Language.Dutch, Locale.Language.German,
               Locale.Language.Italian, Locale.Language.Danish]
  primary_provider = True
  accepts_from = ['com.plexapp.agents.localmedia']
  contributes_to = ['com.plexapp.agents.imdb']

  def search(self, results, media, lang):
    if media.primary_metadata is not None and RE_IMDB_ID.search(media.primary_metadata.id):
      results.Append(MetadataSearchResult(
        id = media.primary_metadata.id,
        score = 100
      ))
    else:
      if media.year and int(media.year) > 1900:
        year = media.year
      else:
        year = ''

      tmdb_dict = self.get_json(url=TMDB_SEARCH_URL % (String.Quote(media.name), year, lang))

      if tmdb_dict and 'results' in tmdb_dict:
        for i, movie in enumerate(sorted(tmdb_dict['results'], key=lambda k: k['popularity'], reverse=True)):
          score = 90
          score = score - abs(String.LevenshteinDistance(movie['title'].lower(), media.name.lower()))

          # Adjust score slightly for 'popularity' (helpful for similar or identical titles when no media.year is present)
          score = score - (5 * i)

          if 'release_date' in movie and movie['release_date'] != '':
            release_year = int(movie['release_date'].split('-')[0])
          else:
            release_year = None

          if media.year and int(media.year) > 1900 and release_year:
            year_diff = abs(int(media.year) - release_year)

            if year_diff <= 1:
              score = score + 10
            else:
              score = score - (5 * year_diff)

          if score <= 0:
            continue
          else:
            results.Append(MetadataSearchResult(
              id = str(movie['id']),
              name = movie['title'],
              year = release_year,
              score = score,
              lang = lang
            ))

  def update(self, metadata, media, lang):
    proxy = Proxy.Preview
    tmdb_dict = self.get_json(url=TMDB_MOVIE_URL % (metadata.id, lang))
    # This second request is necessary since full art/poster lists are not returned if they don't exactly match the language
    tmdb_images_dict = self.get_json(url=TMDB_IMAGES_URL % metadata.id)

    if tmdb_dict is None or tmdb_images_dict is None:
      return None

    # Rating.
    votes = tmdb_dict['vote_count']
    rating = tmdb_dict['vote_average']
    if votes > 3:
      metadata.rating = rating

    # Title of the film.
    metadata.title = tmdb_dict['title']

    if 'original_title' in tmdb_dict and tmdb_dict['original_title'] != tmdb_dict['title']:
      metadata.original_title = tmdb_dict['original_title']

    # Tagline.
    metadata.tagline = tmdb_dict['tagline']

    # Release date.
    try:
      metadata.originally_available_at = Datetime.ParseDate(tmdb_dict['release_date']).date()
      metadata.year = metadata.originally_available_at.year
    except:
      pass

    if Prefs['country'] != '':
      c = Prefs['country']

      for country in tmdb_dict['releases']['countries']:
        if country['iso_3166_1'] == TMDB_COUNTRY_CODE[c]:

          # Content rating.
          if 'certification' in country and country['certification'] != '':
            if TMDB_COUNTRY_CODE[c] == 'US':
              metadata.content_rating = country['certification']
            else:
              metadata.content_rating = '%s/%s' % (TMDB_COUNTRY_CODE[c].lower(), country['certification'])

          # Release date (country specific).
          if 'release_date' in country and country['release_date'] != '':
            metadata.originally_available_at = Datetime.ParseDate(country['release_date']).date()

          break

    # Summary.
    metadata.summary = tmdb_dict['overview']
    if metadata.summary == 'No overview found.':
      metadata.summary = ""

    # Runtime.
    try: metadata.duration = int(tmdb_dict['runtime']) * 60 * 1000
    except: pass

    # Genres.
    metadata.genres.clear()
    for genre in tmdb_dict['genres']:
      metadata.genres.add(genre['name'].strip())

    # Collections.
    metadata.collections.clear()
    if Prefs['collections'] and tmdb_dict['belongs_to_collection'] is not None:
      metadata.collections.add(tmdb_dict['belongs_to_collection']['name'].replace(' Collection',''))

    # Studio.
    try: metadata.studio = tmdb_dict['production_companies'][0]['name'].strip()
    except: pass

    # Country.
    metadata.countries.clear()
    if 'production_countries' in tmdb_dict:
      for country in tmdb_dict['production_countries']:
        country = country['name'].replace('United States of America', 'USA')
        metadata.countries.add(country)

    # Cast.
    metadata.directors.clear()
    metadata.writers.clear()
    metadata.producers.clear()
    metadata.roles.clear()
    config_dict = self.get_json(url=TMDB_CONFIG_URL, cache_time=CACHE_1MONTH * 3)

    for member in tmdb_dict['casts']['crew']:
      if member['job'] == 'Director':
        metadata.directors.add(member['name'])
      elif member['job'] in ('Writer', 'Screenplay'):
        metadata.writers.add(member['name'])
      elif member['job'] == 'Producer':
        metadata.producers.add(member['name'])

    for member in tmdb_dict['casts']['cast']:
      role = metadata.roles.new()
      role.role = member['character']
      role.actor = member['name']
      if member['profile_path'] is not None:
        role.photo = config_dict['images']['base_url'] + 'original' + member['profile_path']

    # Note: for TMDB artwork, number of votes is a far better predictor of quality than average rating.
    # Popular posters for very popular movies have vote counts in the 20-30 range, so we'll boost/discount by a healthy margin.

    valid_names = list()
    for i, poster in enumerate(tmdb_images_dict['posters']):

      # Boost the score for localized posters (according to the preference).
      if Prefs['localart']:
        if poster['iso_639_1'] == lang:
          tmdb_images_dict['posters'][i]['vote_count'] = float(poster['vote_count']) + VOTE_COUNT_BOOST
    
      # Discount score for foreign posters.
      if poster['iso_639_1'] != lang and poster['iso_639_1'] is not None and poster['iso_639_1'] != 'en':
        tmdb_images_dict['posters'][i]['vote_count'] = float(poster['vote_count']) - VOTE_COUNT_BOOST

    for i, poster in enumerate(sorted(tmdb_images_dict['posters'], key=lambda k: k['vote_count'], reverse=True)):
      if i > ARTWORK_ITEM_LIMIT:
        break
      else:
        poster_url = config_dict['images']['base_url'] + 'original' + poster['file_path']
        thumb_url = config_dict['images']['base_url'] + 'w154' + poster['file_path']
        valid_names.append(poster_url)

        if poster_url not in metadata.posters:
          try: metadata.posters[poster_url] = proxy(HTTP.Request(thumb_url), sort_order=i+1)
          except: pass

    metadata.posters.validate_keys(valid_names)

    valid_names = list()
    for i, backdrop in enumerate(tmdb_images_dict['backdrops']):
  
      # Boost the score for localized art (according to the preference).
      if Prefs['localart']:
        if backdrop['iso_639_1'] == lang:
          tmdb_images_dict['backdrops'][i]['vote_count'] = float(backdrop['vote_count']) + VOTE_COUNT_BOOST

      # Discount score for foreign art.
      if backdrop['iso_639_1'] != lang and backdrop['iso_639_1'] is not None and backdrop['iso_639_1'] != 'en':
        tmdb_images_dict['backdrops'][i]['vote_count'] = float(backdrop['vote_count']) - VOTE_COUNT_BOOST

    for i, backdrop in enumerate(sorted(tmdb_images_dict['backdrops'], key=lambda k: k['vote_count'], reverse=True)):
      if i > ARTWORK_ITEM_LIMIT:
        break
      else:
        backdrop_url = config_dict['images']['base_url'] + 'original' + backdrop['file_path']
        thumb_url = config_dict['images']['base_url'] + 'w300' + backdrop['file_path']
        valid_names.append(backdrop_url)

        if backdrop_url not in metadata.art:
          try: metadata.art[backdrop_url] = proxy(HTTP.Request(thumb_url), sort_order=i+1)
          except: pass

    metadata.art.validate_keys(valid_names)

  def get_json(self, url, cache_time=CACHE_1MONTH):
    # try n times waiting 5 seconds in between if something goes wrong
    tmdb_dict = None

    for t in reversed(range(REQUEST_RETRY_LIMIT)):
      try:
        tmdb_dict = JSON.ObjectFromURL(url, sleep=2.0, cacheTime=cache_time)
      except:
        Log('Error fetching JSON from TheMovieDB, will try %s more time(s) before giving up.', str(t))
        time.sleep(5)

      if isinstance(tmdb_dict, dict):
        return tmdb_dict

    Log('Error fetching JSON from TheMovieDB')
    return None
