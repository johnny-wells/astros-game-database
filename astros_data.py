'''
This script retrieves the previous day's Astros box score from Baseball 
Reference using browser automation (Selenium), formats the box score, and saves
it as a csv file. I plan to add more code that will upload the box score to a 
MySQL database and have each player's stats for each game in one table that I 
can query. It runs automatically each morning via windows task scheduler.
'''

import selenium
from selenium  import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import Select

import time
from time import strftime
from datetime import datetime, timedelta
import pandas as pd
import shutil
import os
import sys


# date/year/month/day variables for yesterday
yd_date = str(datetime.now() - timedelta(days = 1))[0:10].replace('-','')
yd_yr = yd_date[0:4]
yd_mo = yd_date[4:6]
yd_da = yd_date[6:]

# standard selenium setup
# chrome driver manager eliminates need to manually update chromedriver
driver = webdriver.Chrome(ChromeDriverManager().install())
action = webdriver.ActionChains(driver)


### SCHEDULE DOWNLOAD ###

schedule_csv_url = ('https://www.ticketing-client.com/ticketing-client/csv/' +
                    'GameTicketPromotionPrice.tiksrv?team_id=117&display_in' +
                    '=singlegame&ticket_category=Tickets&site_section=Defau' +
                    'lt&sub_category=Default&leave_empty_games=true&event_t' +
                    'ype=T&year=2024&begin_date=20240201')

# schedule auto-downloads when visiting the url. Downloading fresh every day.
driver.get(schedule_csv_url)

# loop until file is found (aka schedule is downloaded)
while True:
    if os.path.exists(
            r'C:\Users\jwell\Downloads\GameTicketPromotionPrice.csv'):
        break
    time.sleep(3)
        
# move dl from downloads to stros folder and rename with today's date
shutil.move(r'C:\Users\jwell\Downloads\GameTicketPromotionPrice.csv',
            ('C:\\Users\\jwell\\OneDrive\\Desktop\\stros\\sched_dls\\'
             + yd_date + '.csv'))

# load schedule into dataframe
sched = pd.read_csv('C:\\Users\\jwell\\OneDrive\\Desktop\\stros\\sched_dls\\' + 
            yd_date + '.csv' , index_col='START DATE')

# find yesterday's matchup by looking up yesterday's date in the dataframe
try:
    matchup = sched.loc[yd_mo + '/'  + yd_da + '/' + yd_yr[2:] , 'SUBJECT']
except:
    sys.exit('No game yesterday')
    
# find home team by returning all characters after the " at " in matchup
home_team = matchup[matchup.find(' at ') + 4:]

# load mlb team reference sheet into dataframe
teams = pd.read_csv(r'C:\Users\jwell\OneDrive\Desktop\stros\mlb teams.csv',
                    index_col='nickname')

# find three letter baseball reference code for the home team
# to use in box score url
code = teams.loc[home_team , 'box']


### BOX SCORE DOWNLOAD ###

# scroll down in browswer to yesterday's box score on baseball reference
bbref_box = ('https://www.baseball-reference.com/boxes/')
driver.get(bbref_box + code + '/' + code + yd_date + '0.shtml')
driver.maximize_window()
body = driver.find_element_by_css_selector('body')
body.send_keys(Keys.PAGE_DOWN)
time.sleep(1) # prevents next steps from running before we finish scrolling

# hover over astros box score 'share & export' button to get drop down menu
share_button = driver.find_element_by_xpath('//*[@id="HoustonAstrosbatting_s' +
                                            'h"]/div/ul/li[1]')
action.move_to_element(share_button).perform()
time.sleep(2)

# click 'get table as csv.' Doesn't download, but exposes box score in the html
get_table = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="HoustonAstrosbat' +
                                'ting_sh"]/div/ul/li[1]/div/ul/li[3]/button')))
get_table.click()

# web element containing the box score
holy_grail = WebDriverWait((driver), 5).until(
        EC.presence_of_element_located((By.ID, 'csv_HoustonAstrosbatting')))

# get text from web element and remove irrelevant text before & after box score
hg_text = holy_grail.text
box_score_string = hg_text[80:hg_text.find(',,,,,,,,,,,,,,,,,,,,,,,,')]

# write box score to csv file named with the date of the game
with open(r'C:\Users\jwell\OneDrive\Desktop\stros\box_scores\box_' + yd_date +
'.csv','w') as f:
    f.write(box_score_string)
    
# open csv in datafram to clean up a formatting issue
temp_df = pd.read_csv(r'C:\Users\jwell\OneDrive\Desktop\stros\box_scores\box_'
                       + yd_date + '.csv' , encoding='ANSI')

def find_nth(string , substring , n):
    """
    returns the position of the nth occurence of a substring within a string
    """
    start = string.find(substring)
    while start >= 0 and n > 1:
        start = string.find(substring , start + len(substring))
        n = n - 1
    return start

# find the start position of each 2nd space in temp_df['Batting']
# so we can eventually remove all characters after it
# will need a solution for players w/ more than 2 spaces (eg Elly De La Cruz)
second_spaces = []
for i in temp_df['Batting']:
    x = find_nth(i , ' ' , 2)
    second_spaces.append(x)
    
# remove all characters after 2nd space and save to list
player_names = []
k = 0
for i in temp_df['Batting']:
    player_names.append(i[0:second_spaces[k]])
    k = k + 1

# replace values in 'Batting' column with values from player_names list
# did not think this formatting issue would take 30 lines to fix lol
temp_df['Batting'] = player_names

# save dataframe to csv (overwrite the csv we just loaded into the dataframe)
temp_df.to_csv(r'C:\Users\jwell\OneDrive\Desktop\stros\box_scores\box_' +
               yd_date + '.csv')