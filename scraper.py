import scraperwiki
import lxml.html
import datetime
import urlparse

#nz2008
#urlToScrape = "http://tracking.ironmanlive.com/newathlete.php?rid=133&race=newzealand&bib=%s&v=3.0&beta=&1378263600"

#Ironman Cairns 2013
urlToScrape = "http://tracking.ironmanlive.com/newathlete.php?rid=1143239999&race=cairns&bib=%s&v=3.0&beta=&1378384200"

#Ironman Boulder 2015
http://track.ironman.com/newathlete.php?rid=2147483711&race=boulder70.3&bib=%s&v=3.0&beta=&1434469500



#Global flag indicating we are scraping for first time
isReset = True
maxBibID = 10
#maxBibID = 50
isDebug = False

def getRaceName():
    return  urlparse.parse_qs(urlparse.urlparse(urlToScrape ).query)['race'][0];

def databaseSetup():
    print "Resetting database and prepopulating Bibs"
    scraperwiki.sqlite.execute("drop table if exists RESULTS")
    scraperwiki.sqlite.commit()

    scraperwiki.sqlite.execute("""CREATE TABLE IF NOT EXISTS "RESULTS" (RACE_NAME,BIB INT,SCRAPED,HAS_RESULTS INT,ATHLETE_NAME,DIVISION INT,AGE INT,STATE,COUNTRY,PROFESSION, DIVISION_RANK INT,         OVERALL_RANK INT,TOTAL_SWIM,TOTAL_BIKE,TOTAL_RUN,TOTAL_TIME,T1,T2)""")
    scraperwiki.sqlite.commit()

    #prepopulate table with bibId's to scrape
    bibIDs = [ {"BIB":x}  for x in range(1,maxBibID +1) ]           
    scraperwiki.sqlite.save(unique_keys=['BIB'], data=bibIDs, table_name="RESULTS")
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


def parsePage(html):
    
    # Dictionary to store info
    athInfo = {}
    
    #Now start populating our data object
    athInfo['ATHLETE_NAME'] = html.cssselect("h2")[0].text
    athInfo['DIVISION_RANK'] = html.cssselect("#rank *")[0].tail.strip()
    athInfo['OVERALL_RANK'] = html.cssselect("#div-rank *")[0].tail.strip()    

    #infoFields = ['BIB', 'DIVISION', 'AGE', 'STATE', 'COUNTRY', 'PROFESSION']
    infoFields = ['BIB', 'DIVISION', 'STATE', 'COUNTRY', 'PROFESSION']
    detailsFields = ['TOTAL_SWIM', 'TOTAL_BIKE', 'TOTAL_RUN', 'TOTAL_TIME']
    
    rows = html.cssselect("table#general-info tr")
    for i, stat in enumerate(infoFields):
        athInfo[stat] = rows[i][1].text
    
    rows = html.cssselect("table#athelete-details tr")
    for i, stat in enumerate(detailsFields):
        athInfo[stat] = rows[i][1].text

    #have to use xpath to get T1 and T2 data
    athInfo['T1'] = html.xpath("//tr[contains(td/text(), 'T1:')]/td[2]")[0].text_content()
    athInfo['T2'] = html.xpath("//tr[contains(td/text(), 'T2:')]/td[2]")[0].text_content()

    athInfo['HAS_RESULTS'] = 1
    athInfo['SCRAPED'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scraperwiki.sqlite.save(unique_keys=['BIB'], data=athInfo, table_name="RESULTS", verbose=0)


#Setup the database
if isReset:
    databaseSetup()


#fetch out bibs to process
athletesToScrape = scraperwiki.sqlite.select('* from "RESULTS" where SCRAPED is null')
print "About to process %s bibs" % len(athletesToScrape);


#This is the main loop that controls which URL to scrape
for athlete in athletesToScrape:
    #call scrape and send to parseHTML 
    pageToScrape = scraperwiki.scrape(urlToScrape % athlete['BIB'])
    html = lxml.html.fromstring(pageToScrape)  

    if isDebug:
        parsePage(html)
    else:
        try:
            parsePage(html)
        except IndexError:
            scraperwiki.sqlite.save(unique_keys=['BIB'], data={'BIB':athlete['BIB'],'HAS_RESULTS':0,'SCRAPED':datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, table_name="RESULTS", verbose=0)
            scraperwiki.sqlite.commit()

#Clean up the data
databaseCleanup()
    
