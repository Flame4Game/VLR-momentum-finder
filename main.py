import re
from bs4 import BeautifulSoup
import requests

def findDataOfMatch(matchNum):
    """
    Scrapes match data from vlr.gg for a specific match ID.
    
    Args:
        matchNum: The match ID/number from vlr.gg
        
    Returns:
        List of tuples containing (round_number, winning_team_name)
    """
    # Construct URL and set up request headers
    url = f'https://www.vlr.gg/{matchNum}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:35.0) Gecko/20100101 Firefox/35.0'
    }

    # Make the request and parse the HTML
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find key elements on the page
    match_header = soup.find("div", class_="match-header-vs")
    rounds = soup.find_all("div", class_="vlr-rounds-row-col")

    # Extract team information
    team1_section = match_header.find("a", class_="match-header-link wf-link-hover mod-1")
    team2_section = match_header.find("a", class_="match-header-link wf-link-hover mod-2")
    team1_name = team1_section.find("div", class_="wf-title-med").text.strip()
    team2_name = team2_section.find("div", class_="wf-title-med").text.strip()

    round_results = []
    is_team1_t = False  # Initialize side tracking (T=attack, CT=defense)
    
    # Find first round to determine initial team sides
    first_round = None
    for rnd in rounds:
        round_num_tag = rnd.find("div", class_="rnd-num")
        if round_num_tag and round_num_tag.text.strip() == "1":
            first_round = rnd
            break
    
    # Determine which team starts on T side
    if first_round:
        squares = first_round.find_all("div", class_="rnd-sq")
        
        if len(squares) >= 2:
            team1_has_t = 'mod-t' in ' '.join(squares[0].get('class', []))
            team2_has_ct = 'mod-ct' in ' '.join(squares[1].get('class', []))
            
            is_team1_t = team1_has_t or team2_has_ct
            
    # Process each round
    for rnd in rounds:
        round_num_tag = rnd.find("div", class_="rnd-num")

        if round_num_tag:
            round_num = round_num_tag.text.strip()
            round_num = int(round_num)
        else:
            continue 
        
        # Determine if T or CT won this round
        t_win = rnd.find("div", class_="rnd-sq mod-win mod-t")
        ct_win = rnd.find("div", class_="rnd-sq mod-win mod-ct")
        
        if t_win:
            tresult = "T-Win"
        elif ct_win:
            tresult = "CT-Win"
        else:
           continue
        
        # Handle team side swaps
        newisTeam1T = is_team1_t
       
        # First side swap at round 13 (standard half)
        if round_num >= 13:
            newisTeam1T = not is_team1_t
            
        # Additional side swaps in overtime (every 2 rounds)
        if round_num >= 25:
            newisTeam1T = round_num % 2 == 1 if is_team1_t else round_num % 2 == 0
            
        # Determine which team won the round based on sides and result
        if (tresult == "T-Win" and newisTeam1T) or (tresult == "CT-Win" and not newisTeam1T):
            result = team1_name
        else:
            result = team2_name

        round_results.append((round_num, result))
        
    return round_results

def getMatchNumsFromTeam(teamNum, numOfMatches):
    """
    Gets data from multiple matches for a specific team.
    
    Args:
        teamNum: The team ID from vlr.gg
        numOfMatches: Number of recent matches to analyze
        
    Returns:
        List of match data, where each match contains round results
    """
    url = f'https://www.vlr.gg/team/matches/{teamNum}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:35.0) Gecko/20100101 Firefox/35.0'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    resultsBlock = soup.find("div", class_="mod-dark", style="margin-bottom: 25px;")
    linkNums = resultsBlock.find_all("a", class_="wf-card fc-flex m-item", href=True)
    
    match_data = []
    tempCount = 0
    for link in linkNums:
        if tempCount >= numOfMatches:
            break
        href = link['href']
        match = re.match(r"/(\d+)", href)
        if match:
            match_rounds = findDataOfMatch(match.group(1))  
            match_data.append(match_rounds) 
            tempCount += 1
    
    return match_data

def getTeamName(teamNum):
    """
    Gets the team name from their team page.
    
    Args:
        teamNum: The team ID from vlr.gg
        
    Returns:
        Team name as a string
    """
    url = f'https://www.vlr.gg/team/matches/{teamNum}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:35.0) Gecko/20100101 Firefox/35.0'
    }

    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    team_header = soup.find("div", class_="team-header-name")
    namee = team_header.find("h1", class_="wf-title").text.strip()
    return(namee)

def split_into_maps(rounds):
    """
    Splits round data into separate maps.
    
    Args:
        rounds: List of (round_num, winner) tuples
        
    Returns:
        List of maps, where each map contains its round data
    """
    maps = []
    current_map = []
    for round_num, winner in rounds:
        if round_num == 1 and current_map: 
            maps.append(current_map)
            current_map = []
        current_map.append((round_num, winner))
    if current_map:
        maps.append(current_map)
    return maps

def analyze_momentum(teamNumber, numOfGamesWanted):
    """
    Analyzes momentum by checking how likely a team is to win after winning X of the last 5 rounds.
    
    Args:
        teamNumber: The team ID from vlr.gg
        numOfGamesWanted: Number of recent matches to analyze
    """
    conditions = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0, 0: 0}  # Counters for different win streak conditions
    success_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0, 0: 0}  # Counters for successful followups
    match_data = getMatchNumsFromTeam(teamNumber, numOfGamesWanted)
    teamName = getTeamName(teamNumber)
    
    for match in match_data:
       maps = split_into_maps(match)
       for map_rounds in maps:
           round_winners = [winner for _, winner in map_rounds] 
           for i in range(len(round_winners) - 5): 
                last_5 = round_winners[i:i+5]  # Get the last 5 rounds
                next_round = round_winners[i+5]  # Get the next round (to check if they win)
                
                wins = last_5.count(teamName)  # Count how many of the last 5 rounds the team won
                
                # Update condition counters
                for theNumber in range(6):
                    if wins == theNumber:
                        conditions[theNumber] += 1
                        if next_round == teamName:
                            success_counts[theNumber] += 1
       
    # Calculate success rates
    success_rates = {}
    for k in conditions:
        if conditions[k] > 0:
            success_rates[k] = success_counts[k] / conditions[k]
        else:
            success_rates[k] = 0
    
    print(f"Team Name: {teamName}")
    
    # Print results in descending order of win streak length
    for k in sorted(success_rates.keys(), reverse=True):
        rate = success_rates[k] * 100
        print(f"{k}/5 win streak: {success_counts[k]} successful cases out of {conditions[k]} total ({rate:.2f}% success rate)")

def calculate_overall_winrate(teamNumber, numOfGamesWanted):
    """
    Calculates the overall round win rate for a team.
    
    Args:
        teamNumber: The team ID from vlr.gg
        numOfGamesWanted: Number of recent matches to analyze
        
    Returns:
        Tuple of (rounds_won, total_rounds, winrate_percentage)
    """
    match_data = getMatchNumsFromTeam(teamNumber, numOfGamesWanted)
    teamName = getTeamName(teamNumber)
    
    total_rounds = 0
    team_wins = 0
    
    for match in match_data:
        for round_num, winner in match:
            total_rounds += 1
            if winner == teamName:
                team_wins += 1
    
    winrate = (team_wins / total_rounds) * 100 if total_rounds > 0 else 0
    
    print(f"\nOverall Round Winrate for {teamName}:")
    print(f"Rounds Won: {team_wins}")
    print(f"Total Rounds: {total_rounds}")
    print(f"Winrate: {winrate:.2f}%")
    
    return team_wins, total_rounds, winrate

# Main execution block
print("What is the team number?")
skbidi = int(input())
print("How many matches back are you looking to analyze? (maximum: 50)")
toilet = int(input())
if toilet > 50:
    print("Too large.")
else:
    print(f"Here is the momentum data you're looking for for team number {skbidi} in {toilet} matches:")
    analyze_momentum(skbidi, toilet)
    print("\nCalculating overall round winrate...")
    calculate_overall_winrate(skbidi, toilet)