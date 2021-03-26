# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions

from typing import Any, Text, Dict, List

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


#-----------------------------------------------------------------------------------------------------------------

# "/discover/movie" to find out about movies based on a certain queary

# examples api requests:
# Find action movies: https://api.themoviedb.org/3/discover/movie?api_key=da97468eeb7c67859a34de57ae6c2880&language=en-US&sort_by=popularity.desc&include_adult=true&include_video=false&page=1&with_genres=28 
# Fight Club data: https://api.themoviedb.org/3/movie/550?api_key=da97468eeb7c67859a34de57ae6c2880
# more examples: https://www.themoviedb.org/documentation/api/discover 

# da97468eeb7c67859a34de57ae6c2880

#API key for v3
#api_key = da97468eeb7c67859a34de57ae6c2880
#base_path = "https://api.themoviedb.org/3/discover/movie?api_key="

QUERIES = {
    "base" : "https://api.themoviedb.org/3/discover/movie?api_key=", 
    "api_key" : "da97468eeb7c67859a34de57ae6c2880",
    "language" : "language=en-US",
    "sort" : {
        "popularity_descent" : "sort_by=popularity.desc",
        "revenue_descent" : "sort_by=revenue.desc"
    },
    "adult" : {
        "true" : "include_adult=true",
        "false" : "include_adult=false"
    },
    "page" : "page=1", #each page is like 20 movies, I would hope we don't need to make something so complex that needs more that 20 movies oh god oh please
    "genre" : "with_genres=", #e.g. with_genres=28
    "starring" : "with_cast=", 
    "director" : "with_crew="
}

GENRES = {
    "action" : "28",
    "adventure" : "12",
    "animation" : "16",
    "comedy" : "35",
    "crime" : "80",
    "documentary" : "99",
    "drama" : "18",
    "family" : "10751",
    "fantasy" : "14",
    "history" : "36",
    "horror" : "27",
    "music" : "10402",
    "mystery" : "9648",
    "romance" : "10749",
    "science fiction" : "878",
    "TV movie" : "10770",
    "thriller" : "53",
    "war" : "10752",
    "western" : "37"
}

#Something that hopefully I won't use v
#API Read Access Token (v4 auth): eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJkYTk3NDY4ZWViN2M2Nzg1OWEzNGRlNTdhZTZjMjg4MCIsInN1YiI6IjYwMmQ1Zjc0OGFjM2QwMDAzZWNjN2FmNyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.K8k-HVdSvZBPIOqrO0qmk2WUjP7Bla9dxc84hJHO5Do

#-----------------------------------------------------------------------------------------------------------------

#Find the person ID number. Assumes given name parametre is not null
def _find_person_id(name: Text) -> Text:
    
    path = "https://api.themoviedb.org/3/search/person?api_key=da97468eeb7c67859a34de57ae6c2880&language=en-US&include_adult=false&page=1&query="

    #The name should either be just the surname( "Cruise" ), or multiple strings joined by a "%20" string(e.g. "tom%20cruise" )
    name_bits = name.split(" ")
    
    if(len(name_bits) == 1):
        path += name_bits[0]
    else:  #assumes parametre is not null and thus if the list generated from slpit isn't 1 it must be more than that
        path += "%20".join(name_bits)

    # I might want to store this information 
    results = requests.get(path).json().get("results")
    if(len(results) > 0):
        person_info = results[0] #get the most popular person with that name
        person_id = person_info["id"] #EXTRACT THE NUMBER ID OF THE PERSON TO BE THEN RETURNED

        return str(person_id)
    else:
        return None


def _find_movies(genre, starring, director) -> List[Dict]:
    """Returns json of facilities matching the search criteria."""

    path = QUERIES["base"] + QUERIES["api_key"]
    path += "&" + QUERIES["sort"]["popularity_descent"] + "&" + QUERIES["adult"]["false"] + "&" + QUERIES["page"] #standard queries

    if genre is not None:   
        path += "&" + QUERIES["genre"] + GENRES[genre.lower()]

    if starring is not None:
        id = _find_person_id(starring)
        if id: #only look for something if an actor with that name was actually found.
            path += "&" + QUERIES["starring"] + id

    if director is not None:
        id = _find_person_id(director)
        if id: #only look for a movie by that director if we find them in the database
            path += "&" + QUERIES["director"] + id
    
    results = requests.get(path).json()
    return results

# A function that retrieves the info about the given movie and outputs the string of its director
# Input should be the id of the movie gotten beforehand, in String form
def _get_director(movie_id: Text): 

    # An API call like this is needed: https://api.themoviedb.org/3/movie/550/credits?api_key=da97468eeb7c67859a34de57ae6c2880&language=en-US
    # Then iterate through the crew and
    # keep the info about the person that matches the "job": "Director". 

    path = "https://api.themoviedb.org/3/movie/" + movie_id + "/credits?api_key=da97468eeb7c67859a34de57ae6c2880&language=en-US"
    results = requests.get(path).json()

    for crew_member in results["crew"]:
        if crew_member["job"] == "Director":
            return crew_member["name"]

    return None

# A function that, given a movie ID, looks through the database and retrieves the first cast member object
# which, hopefully, is the protagonist
def _get_starring(movie_id: Text): 
    
    # An API call like this is needed: https://api.themoviedb.org/3/movie/550/credits?api_key=da97468eeb7c67859a34de57ae6c2880&language=en-US
    # Navigate to "cast" and retrieve the info of the first item in the list. 
    # This will be the protagonist. Than return its object "name"

    path = "https://api.themoviedb.org/3/movie/" + movie_id + "/credits?api_key=da97468eeb7c67859a34de57ae6c2880&language=en-US"
    results = requests.get(path).json()
    
    return results["cast"][0]["name"]

# A function that returns the genre of a movie, given the json data of that movie
def _get_genre(movie_id: Text): 

    # An API call to get the data about the movie
    # Example call: https://api.themoviedb.org/3/movie/550?api_key=da97468eeb7c67859a34de57ae6c2880

    path = "https://api.themoviedb.org/3/movie/" + movie_id + "?api_key=da97468eeb7c67859a34de57ae6c2880"
    results = requests.get(path).json()

    # Get the name of the first genre in the list given. 
    return results["genres"][0]["name"]

#This is the action a user calls for when they want to start a new search (so it empties all slots)
class ActionOffer(Action):

    def name(self) -> Text:
        return "action_offer"

    def run(self, dispatcher: CollectingDispatcher, 
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        #the function should empty every slot, so that the user can start a new search from scratch

        genre = tracker.get_slot("genre")
        starring_name = tracker.get_slot("starring_name") 
        starring_surname = tracker.get_slot("starring_surname")
        if starring_name or starring_surname:
            starring = str(starring_name) + " " + str(starring_surname)
        else:
            starring = None
        print("starring: " + str(starring))
        director_name = tracker.get_slot("director_name") 
        director_surname = tracker.get_slot("director_surname")
        if director_name or director_surname:
            director = str(director_name) + " " + str(director_surname)
        else:
            director = None
        print("director: " + str(director))
        offers_already_given = tracker.get_slot("offers_already_given")

        results = _find_movies(genre, starring, director).get("results")

        if len(results) == 0:  #TODO: Gotta set existing slots perhaps huh
            dispatcher.utter_message( "Sorry, we could not find a movie like that" )
            return [SlotSet("genre", None), 
                SlotSet("starring_name", None),
                SlotSet("starring_surname", None),
                SlotSet("director_name", None),
                SlotSet("director_surname", None),
                SlotSet("title", None)]
        
        num = len(results)
        movies_number = str(num)
        if num > 10:
            movies_number = "a lot of"

        # based on what movies we've already seen before, 
        # let us only retrieve the first movie we run into that we haven't already offered the user
        i = 0 # movie index that helps us navigate the results (page is at max 20 results)
        movie_id = results[i]["id"]
        while (movie_id in offers_already_given) and i<20 and i<len(results)-1: #first it had: "and i<len(offers_already_given)" but I don't get why
            i += 1
            movie_id = results[i]["id"]

        if i>=len(results)-1:  #TODO: Gotta set existing slots perhaps huh
            dispatcher.utter_message( "Sorry, we could not find a movie like that" )
            return [SlotSet("genre", None), 
                SlotSet("starring_name", None),
                SlotSet("starring_surname", None),
                SlotSet("director_name", None),
                SlotSet("director_surname", None),
                SlotSet("title", None)]

        offers_already_given.append(movie_id) # remember in the future that the we have offered this movie
        title = results[i]["title"]  # get and set (in the return) the title slot for the movie

        #TODO: check if these if statements are any useful or actually detrimental
        if genre is None:
            genre = _get_genre(  str( movie_id ) )

        if starring is None:
            starring = _get_starring( str( movie_id ) )
        
        if director is None:
            director = _get_director( str( movie_id ) )
        
        rating = str(results[i]["vote_average"]) # get the rating for the movie and make it a string
        
        #dispatcher.utter_message(text="I have {} options for you. What do you think about {}? Then I have {}. Then I have {}".format(movies_number, movie_titles[0], movie_titles[1], movie_titles[2]))
        dispatcher.utter_message(text="I have {} options for you. What do you think about {}? This movie's average rating is {}.".format(movies_number, title, rating))

        return [SlotSet("info_genre", genre), 
                SlotSet("info_starring", starring), 
                SlotSet("info_director", director), 
                SlotSet("aggregate_rating", rating), 
                SlotSet("title", title), 
                SlotSet("offers_already_given", offers_already_given)]

# This is the action a user calls for when they want to know some info about the movie
# it uses the slots "director", "starring" and "genre". Depending on what info has the user asked for, 
class ActionGiveInfo(Action):
    def name(self) -> Text:
        return "action_give_info"

    def run(self, dispatcher: CollectingDispatcher, 
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        genre_was_requested = tracker.get_slot("requested_info_genre")
        starring_was_requested = tracker.get_slot("requested_info_starring")
        director_was_requested = tracker.get_slot("requested_info_director")
        genre, starring, director = "", "", ""

        if not genre_was_requested and not director_was_requested and not starring_was_requested:
            utterance = "Sorry, you need to select a movie before I can tell you anything about it"
        else: 
            utterance = "It's"

        if genre_was_requested: 
            genre = tracker.get_slot("info_genre")
            utterance += " a {} movie".format(genre.lower()) 

        if director_was_requested:
            director = tracker.get_slot("info_director")
            utterance += " by {}".format(director)

        if starring_was_requested:
            starring = tracker.get_slot("info_starring")
            utterance += " with {}".format(starring)

        #remove the last space and put a period instead
        utterance += "."
        dispatcher.utter_message(text=utterance)

        #clean up the slots in case the user asks for another question
        return [SlotSet("requested_info_genre", False),
                SlotSet("requested_info_starring", False),
                SlotSet("requested_info_director", False) ]