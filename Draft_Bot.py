import requests
import pandas as pd

"""
Author: Samer Harten

Draft_Bot.py replicates a Get request to the API endpoint used by https://fantasy.espn.com/basketball/players/projections
to obtain the statistics of the NBA players of the 2023-2024 season. The NBA players are classified as either rookie, regular,
or Not Applicable (NA) since those players are assumed to not get drafted.

Player classifications meaning:
- Rookies only have projected stats so the equation will only apply to the projected stats.
- Regular players are players that have played at least 1 season before the current season and have projected stats.
- Not Applicable players are players that either don't have projected stats and have played at least 1 season or they
haven't played any seasons and don't have projections for the current season.

This script uses an equation to compute a score rating which is used to rank the players in the order of decreasing priority
to draft by the league member. The equation has a multiplier value for each statistical category. Each multiplier value varies 
based on the importance of the category to the league member. For example, if the member would like to create a team based on
high points scoring, then the multiplier for would be the highest value which is 4. If the user for example doesn't care about
building a team that's focused on blocks, then the blocks category would have the lowest multiplier value of 1.

Multiplier values: 1 (minimum) to 4 (maximum) for favorable categories OR -4 (minimum) to -1 (maximum) for turn overs
Statistical categories used for the computations: points, rebounds, assists, steals, FG%, 3 pointers made, blocks, FT%, turn overs
Equation form: player score = (points_multiplier * average_points) + (rebounds_multiplier * rebounds) + ... - (turn_over_multiplier * turn_overs)

NOTE:
- The equation for the regular players takes both last season performance and projections into perspective but divides
that value by 2 as to have a fair comparison against the rookies.
- The equation for the rookies only takes the projected ratings into perspective.
- There is no equation for NA players as these are generaly players that do not get drafted ideally as odds are, they
won't perform well.

After the equation computes all the player scores, the player names are loaded into a dict as keys and the scores as values,
the tkinter module is used to create a GUI for the league member to enter the names of the players drafted. The list of available
players will decrease the league member inputs their names as they get selected in the draft.

-------------------- How to use --------------------
- User enters the multiplier values showing what categories they'd like their team to specialize in.
- After each of the 9 categories is assigned a multplier score, the list of top 20 NBA players from the draft appears as a
clickable button.
- User will be able to select whichever player has been drafted to upadate the list.
- Whenever the user turn comes in the draft, the top player in the GUI will be the one that the user selects.
- When this player is selected on the fantasy draft application, the NBA player's nane is selected in the GUI tool as to
update the list. The user will also select the name of each player selected by other league memebrs as to keep the list
up to date.
- This continues until the end of the draft. When the draft concludes, the user can exit from the tool.
----------------------------------------------------

NOTE:
- The GUI functionality hasn't been created yet so the user interacts with the tool using command line.
- The multiplier values are changed by updating the mapping_eqn dictionary
"""

url = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons/2024/segments/0/leaguedefaults/1?view=kona_player_info"

mapping_categories = {'0' : "PTS", '3' : "AST", '6' : "REB", '2' : "STL", '19' : "FG_PCT", '17' : "FG3M", '1' : "BLK", '20' : "FT_PCT", '11' : "TOV"}
mapping_eqn = {"PTS" : 4, "AST" : 2, "REB" : 4, "STL" : 2, "FG_PCT" : 4, "FG3M" : 4, "BLK" : 1, "FT_PCT" : 4, "TOV" : -1}
stats_fltrd = {} # form of {key -> 'PTS', value -> 25.08}
proj_fltrd = {} # form of {key -> 'PTS', value -> 25.08}
players = {} # form of {key -> 'Jokic', value -> 234} This holds the name of the player and their score
is_regular = False # variable used to track if player is a regular or not
is_rookie = False # variable used to track if player is a rookie or not
is_na = False # vairable used to track if a player has no projections and hasn't played last season

headers = {
  'authority': 'lm-api-reads.fantasy.espn.com',
  'accept': 'application/json',
  'accept-language': 'en-US,en;q=0.9',
  'cookie': 's_ecid=MCMID%7C50658048473958273273982227904902076908; _cb=CPjxbyDmmbfMCKFHoP; device_d6b61cd=e7fb6934-7107-49be-8d14-1a05ac6778c0; SWID={48D98DC0-4183-491A-96DA-20DB4CA55BD1}; ESPN-ONESITE.WEB-PROD-ac=XCA; espnAuth={"swid":"{48D98DC0-4183-491A-96DA-20DB4CA55BD1}"}; _gcl_au=1.1.1137961383.1696911513; check=true; AMCVS_EE0201AC512D2BE80A490D4C%40AdobeOrg=1; AMCV_EE0201AC512D2BE80A490D4C%40AdobeOrg=-330454231%7CMCIDTS%7C19651%7CMCMID%7C50658048473958273273982227904902076908%7CMCAAMLH-1698372841%7C7%7CMCAAMB-1698372841%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1697775241s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C3.1.2; userZip=m4k%200a1; _omnicwtest=works; tveMVPDAuth=; tveAuth=; ESPN-ONESITE.WEB-PROD.token=5=eyJhY2Nlc3NfdG9rZW4iOiJmNWQwNjA2ZWI4NzU0MTI1YWJkYWEzN2E2YjlkYTliMiIsInJlZnJlc2hfdG9rZW4iOiI3M2M1NWJjZmY3YjQ0YjBiOGQwYzkyMzU2ZDdiMzVjMiIsInN3aWQiOiJ7NDhEOThEQzAtNDE4My00OTFBLTk2REEtMjBEQjRDQTU1QkQxfSIsInR0bCI6ODY0MDAsInJlZnJlc2hfdHRsIjoxNTU1MjAwMCwiaGlnaF90cnVzdF9leHBpcmVzX2luIjpudWxsLCJpbml0aWFsX2dyYW50X2luX2NoYWluX3RpbWUiOjE2OTY5MTE0NjM5OTUsImlhdCI6MTY5Nzc2ODA0NzAwMCwiZXhwIjoxNjk3ODU0NDQ3MDAwLCJyZWZyZXNoX2V4cCI6MTcxMzMyMDA0NzAwMCwiaGlnaF90cnVzdF9leHAiOm51bGwsInNzbyI6bnVsbCwiYXV0aGVudGljYXRvciI6ImRpc25leWlkIiwibG9naW5WYWx1ZSI6bnVsbCwiY2xpY2tiYWNrVHlwZSI6bnVsbCwic2Vzc2lvblRyYW5zZmVyS2V5IjoiY09XV0dsSUVDbDBzZlN1ZlZFN0FyVnJyMkswaVQ4N0ZvaEYwdVJ5VEdZSlFTMGhBWGhOMzItR2NFcDlFVmxkVW51RzVxSW5NaGd2eGJfSlVCOE5QbHI3dzcyeEdIdG5TbTd4ai1NTUpUUU1CMmF0dHZQWSIsImNyZWF0ZWQiOiIyMDIzLTEwLTIwVDAyOjE0OjA3LjAwNloiLCJsYXN0Q2hlY2tlZCI6IjIwMjMtMTAtMjBUMDI6MTQ6MDcuMDA2WiIsImV4cGlyZXMiOiIyMDIzLTEwLTIxVDAyOjE0OjA3LjAwMFoiLCJyZWZyZXNoX2V4cGlyZXMiOiIyMDI0LTA0LTE3VDAyOjE0OjA3LjAwMFoifQ==|eyJraWQiOiJxUEhmditOL0tONE1zYnVwSE1PWWxBc0pLcWVaS1U2Mi9DZjNpSm1uOEJ6dzlwSW5xbTVzUnc9PSIsImFsZyI6IlJTMjU2In0.eyJpc3MiOiJodHRwczovL2F1dGhvcml6YXRpb24uZ28uY29tIiwic3ViIjoiezQ4RDk4REMwLTQxODMtNDkxQS05NkRBLTIwREI0Q0E1NUJEMX0iLCJhdWQiOiJFU1BOLU9ORVNJVEUuV0VCLVBST0QiLCJleHAiOjE2OTc4NTQ0NDcsImlhdCI6MTY5Nzc2ODA0NywianRpIjoiRXI1V1BBM05oZEs2emN5Z1VRVmhudyIsIm5iZiI6MTY5Nzc2Nzk4NywiYV90eXAiOiJPTkVJRF9UUlVTVEVEIiwiYV9jYXQiOiJHVUVTVCIsImF0ciI6ImRpc25leWlkIiwic2NvcGVzIjpbIkFVVEhaX0dVRVNUX1NFQ1VSRURfU0VTU0lPTiJdLCJjX3RpZCI6IjEzMjQiLCJpZ2ljIjoxNjk2OTExNDYzOTk1LCJodGF2IjoyLCJodGQiOjE4MDAsInJ0dGwiOjE1NTUyMDAwLCJlbWFpbCI6InNhbWVyaGFydGVuQHlhaG9vLmNhIn0.V3KZ8V1UnCwGJ6SJzwSn31SkvoxDnULC-l8ornqtASQdBrXuUnTK2-HIxG9R3icuRReTlnnHgsxgSSFtzDrTo-hLVp63qpQm0rK6PoOoFO70eUbOyfRHhCToN_wctbp2M_5qUni2NheqsxtwWb2d7bBb4xE_IKBgoytnRiqYboPz9InqVmAZRL96-TYqOmE827AWRZVXy4iMBku2xD6-FiGji5xCaCTZVQooSiP0C6DIMc7mW9w00MqzqccGop-6I9e_9MldgHwkQQqa5BplDXSWGZC3oRbF94PfFZc6KG1z333xgM82wHp2sq44NB3OeBML74i7nNFGMSVKoOmMAg; s_omni_lid=%5B%5BB%5D%5D; s_cc=true; IR_gbd=espn.com; country=ca; hashedIp=fb89dee7dfa2f1770820d51e6659b8074421fd0b706de4c124b51f9cf97fc44c; nol_fpid=jtuq7vjsrwcopn2wbe4bp9lryafcu1696911449|1696911449107|1697768093727|1697768093729; mbox=PC#51f389a708c84145800ef4c0f85be5d0.34_0#1761012929|session#ec17cc847a1142feb3ff07ffcc4194fc#1697769989; espn_s2=AEASJbatuj5XSCdWbQT4FpNJtl1nQtG82XEzqx6xzqlpoJHBNwKcKTQKOZn0Vdby%2BqqvmEw14u4rfbsvMBz17HIWkz9Lz8lDVd1s0VO3wyFEWXmwAQfkRvGSuiDzG3Qym9fwsuzWiClJVECZIEUnHa2wGTqdnyun6De4g7qG2WNjyM21p8braTC7f7eAQ3mGVr1vDd5Fb0cV%2Bnj9z%2FWzlUq3M7oqKIu%2BNmArMm81AYPZVxwKKIFKNmYKtLw7%2BRJ3XK%2FYLhZLBmkoTqXYqyBIfIBC; ESPN-ONESITE.WEB-PROD.idn=002bde88f3; _chartbeat2=.1606975143621.1697774419564.0000011100000011.hsyfpCFvI1JFr5wYcnv-lC9GO3q.1; _cb_svref=https%3A%2F%2Fwww.google.com%2F; IR_9070=1697774419682%7C0%7C1697774419682%7C%7C; s_c24_s=Less%20than%201%20day; s_gpv_pn=fantasy%3Abasketball%3Aleague%3Atoolsprojections; s_c6=1697774420464-Repeat; s_c24=1697774422880; _chartbeat4=t=CTMnNVCdV1kdpGrqCDgJKhB_gD9x&E=10&x=100&c=20.23&y=10189&w=766; s_ensNR=1697775634367-Repeat; SWID=A40FEF29-AA25-4DAB-CDC7-9C70961DB138',
  'if-none-match': 'W/"06b6c9c6bfa5e15af7fa876977547d452"',
  'origin': 'https://fantasy.espn.com',
  'referer': 'https://fantasy.espn.com/',
  'sec-ch-ua': '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-site',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
  'x-fantasy-filter': '{"players":{"filterStatsForExternalIds":{"value":[2023,2024]},"filterSlotIds":{"value":[0,1,2,3,4,5,6,7,8,9,10,11]},"filterStatsForSourceIds":{"value":[0,1]},"useFullProjectionTable":{"value":true},"sortAppliedStatTotal":{"sortAsc":false,"sortPriority":3,"value":"102024"},"sortDraftRanks":{"sortPriority":2,"sortAsc":true,"value":"STANDARD"},"sortPercOwned":{"sortPriority":4,"sortAsc":false},"limit":994,"filterStatsForTopScoringPeriodIds":{"value":5,"additionalValue":["002024","102024","002023","012024","022024","032024","042024"]}}}',
  'x-fantasy-platform': 'kona-PROD-6d0eeca9415811f7b4ae621bcf7c80fe306e703c',
  'x-fantasy-source': 'kona'
}

response = requests.get(url, headers=headers)
data = response.json()

# There are 50 players per page so run a for-loop that iterates 50 times
for i in range(994):
  df = pd.json_normalize(data['players'][i])
  player_name = df["player.fullName"][0] # Get the player's full name
  
  # If the player.stats column doesn't exist then the player is na
  if "player.stats" not in df.columns:
    is_na = True
  else:
    stats = df["player.stats"].tolist() # Player stats
  
  # Is the player a rookie or not
  try: # If this passes, then player isn't a rookie and has played last season
    # 2023 stats
    stats_2023 = stats[0][0]['averageStats']

    #2024 projections
    proj_2024 = stats[0][-1]['averageStats']

    # Since we got to this point of execution, the player has projections and he played last season so he's a regular
    is_regular = True
    print(f"Obtaining {player_name}'s stats - regular")
  except:
    try: # If this passes then the player is a rookie 
      proj_2024 = data["players"][i]['player']['stats'][4]['averageStats']
      
      # Since we got to this point of execution, the player isn't a regular and he has projections so he's a rookie
      is_rookie = True
      print(f"Obtaining {player_name}'s stats - rookie")
    except: # If execution gets here, the player isn't a rookie and hasn't played last season

      # Since we got to this point of execution, the player isn't a regular and he isn't a rookie so he's an na
      is_na = True
      print(f"Obtaining {player_name}'s stats - na")


  if is_regular: # If player is a regular
    # Updated the filtered stats dictionary for stats & projections
    for stat in stats_2023:
      try:
          stats_fltrd[mapping_categories[stat]] = stats_2023[stat]
          proj_fltrd[mapping_categories[stat]] = proj_2024[stat]
      except:
          pass

    # Applying the equation to the filtered results
    player_rating_score = 0
    for stat in stats_fltrd:
      multiplier = mapping_eqn[stat]
      avg_stat_val = stats_fltrd[stat]
      avg_proj_stat_val = proj_fltrd[stat]
      player_rating_score += (((multiplier * avg_stat_val) + (multiplier * avg_proj_stat_val))/2)

    # Add player and his score to the players dict
    players[player_name] = player_rating_score

  elif is_rookie: # If rookie
    # Updated the filtered stats dictionary for stats & projections
    for stat in proj_2024:
      try:
          proj_fltrd[mapping_categories[stat]] = proj_2024[stat]
      except:
          pass

    # Applying the equation to the filtered results
    player_rating_score = 0
    for stat in proj_fltrd:
      multiplier = mapping_eqn[stat]
      avg_proj_stat_val = proj_fltrd[stat]
      player_rating_score += (multiplier * avg_proj_stat_val)

    # Add player and his score to the players dict
    players[player_name] = player_rating_score
  
  else: # If na
    pass # Do nothing

# Sort the dict items by increasing item value NOTE validate this
players = dict(sorted(players.items(), key=lambda item: item[1], reverse=True))

while(players): # Run the loop until the 
  # Remaining players
  print("\n")
  print("Players to draft\n")

  # show the reamining players at increments of 10 per draft selection 
  x = 10
  curr = 0
  for key in players:
    if curr == x:
      break
    else:
      print(key)
    curr += 1

  # ask user which player has been chosen
  print("\n")
  drafted = input("Which player has been drafted: ")
  
  # Update the dict
  if drafted not in players:
    del(players[drafted])
    print(f"{drafted} has been drafted")
  else:
    print(f"{drafted} has already been removed")

  # to_del = ""

  # for player in players:
  #   name_lst = player.split(" ")
  #   initals = f"{name_lst[0][0]} {name_lst[1][0]}"
  #   if drafted == initals:
  #     to_del = players[player]

  # del(to_del)