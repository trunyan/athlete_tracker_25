import scraperwiki
import requests
import lxml.html
import datetime
import urlparse

#urlToScrape = "http://www.ironman.com/triathlon/events/americas/ironman/louisville/results.aspx?rd=20140824&race=louisville&bidid={}&detail=1#axzz3BqLnCum2"
#urlToScrape = "http://www.ironman.com/triathlon/events/americas/ironman/wisconsin/results.aspx?rd=20140907&race=wisconsin&bidid={}&detail=1#axzz3CpI5sQCm"
#urlToScrape = "http://www.ironman.com/triathlon/events/americas/ironman-70.3/world-championship/results.aspx?rd=20140907&race=worldchampionship70.3&bidid={}&detail=1#axzz3Da0TVGX8"
urlToScrape = "http://www.ironman.com/triathlon/events/americas/ironman/chattanooga/results.aspx?rd=20140928&race=chattanooga&bidid={}&detail=1#axzz3FgVcSk9M"

#Global flag indicating we are scraping for first time
isReset = True
maxBibID = 3000

def getRaceName():
    return  urlparse.parse_qs(urlparse.urlparse(urlToScrape).query)['race'][0];

def databaseSetup():
    print "Resetting database and prepopulating Bibs"
    scraperwiki.sqlite.execute("drop table if exists RESULTS")
    scraperwiki.sqlite.commit()

    scraperwiki.sqlite.execute("""CREATE TABLE IF NOT EXISTS "RESULTS" (RACE_NAME,BIB INT,SCRAPED,HAS_RESULTS INT,ATHLETE_NAME,DIVISION INT,AGE INT,STATE,COUNTRY,PROFESSION, DIVISION_RANK INT, OVERALL_RANK INT,TOTAL_SWIM,TOTAL_BIKE,TOTAL_RUN,TOTAL_TIME,T1,T2, URL)""")
    scraperwiki.sqlite.commit()

    #prepopulate table with bibId's to scrape
    bibIDs = [ {"BIB":x}  for x in range(1,maxBibID +1) ]           
    scraperwiki.sqlite.save(unique_keys=['BIB'], data=bibIDs, table_name="RESULTS")
    scraperwiki.sqlite.commit()  


def buildAthleteInfo(dom):
    
    # Dictionary to store info
    athInfo = {}
    
    infoFields = ['BIB', 'DIVISION', 'AGE', 'STATE', 'COUNTRY', 'PROFESSION']
    detailsFields = ['TOTAL_SWIM', 'TOTAL_BIKE', 'TOTAL_RUN', 'TOTAL_TIME']
    
    #This works just fine
    athInfo['ATHLETE_NAME']  = dom.cssselect("h1")[0].text
    athInfo['DIVISION_RANK'] = dom.cssselect("#rank *")[0].tail.strip()
    athInfo['OVERALL_RANK']  = dom.cssselect("#div-rank *")[0].tail.strip()
    
    rows = dom.cssselect('table#general-info tbody tr')
    for i, stat in enumerate(infoFields):
        athInfo[stat] = rows[i][1].text
    
    rows = dom.cssselect('table#athelete-details tbody tr')
    for i, stat in enumerate(detailsFields):
        athInfo[stat] = rows[i][1].text

    athInfo['T1'] = dom.xpath("//tr[contains(td/text(), 'T1:')]/td[2]")[0].text_content()
    athInfo['T2'] = dom.xpath("//tr[contains(td/text(), 'T2:')]/td[2]")[0].text_content()

    athInfo['HAS_RESULTS'] = 1

    return athInfo


def saveAthlete(athlete, athBib):
    #Check to see if there were any results
    if athlete['BIB'] is None:
        athlete['BIB'] = athBib
        athlete['HAS_RESULTS'] = 0

        
    athlete['SCRAPED'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scraperwiki.sqlite.save(unique_keys=['BIB'], data=athlete, table_name="RESULTS", verbose=0)
    scraperwiki.sqlite.commit()


def databaseCleanup():
    print "running cleanup";

    try:
        scraperwiki.sqlite.execute("update RESULTS set RACE_NAME ='"+ getRaceName() + "'")           
        scraperwiki.sqlite.execute("update RESULTS set DIVISION_RANK = null where trim(DIVISION_RANK) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set OVERALL_RANK = null where trim(OVERALL_RANK) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set TOTAL_SWIM = null where trim(TOTAL_SWIM ) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set TOTAL_BIKE = null where trim(TOTAL_BIKE) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set TOTAL_RUN = null where trim(TOTAL_RUN) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set TOTAL_TIME = null where trim(TOTAL_TIME) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set T1 = null where trim(T1) like '%-%' ")
        scraperwiki.sqlite.execute("update RESULTS set T2 = null where trim(T2) like '%-%' ")
        scraperwiki.sqlite.commit() 
    except scraperwiki.sqlite.SqliteError, e:
        print str(e)

def dumpclean(obj):
    if type(obj) == dict:
        for k, v in obj.items():
            if hasattr(v, '__iter__'):
                print k
                dumpclean(v)
            else:
                print '%s : %s' % (k, v)
    elif type(obj) == list:
        for v in obj:
            if hasattr(v, '__iter__'):
                dumpclean(v)
            else:
                print v
    else:
        print obj

#Setup the database
if isReset:
    databaseSetup()

#fetch out bibs to process
athletesToScrape = scraperwiki.sqlite.select('* from "RESULTS" where SCRAPED is null')
print "About to process %s bibs" % len(athletesToScrape);


#This is the main loop that controls which URL to scrape
for athlete in athletesToScrape:
    athBib = athlete['BIB']
    athlete['URL'] =  urlToScrape.format(athlete['BIB'])
    html = scraperwiki.scrape(athlete['URL'])
    
    try:
        athlete.update(buildAthleteInfo(lxml.html.fromstring(html)))
        saveAthlete(athlete, athBib)
    except IndexError:
        athlete['BIB'] = athBib
        athlete['HAS_RESULTS'] = 3
        scraperwiki.sqlite.save(unique_keys=['BIB'], data=athlete, table_name="RESULTS", verbose=0)
        scraperwiki.sqlite.commit()
 
    #print "----------------------------------------" + str(athBib)
    #print dumpclean(athlete)
    
    
#Clean up the data
databaseCleanup()
