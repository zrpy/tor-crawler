import httpx,asyncio,threading,time,re,sqlite3
base_url="https://ahmia.fi/onions/"


def add_sql(url,title, description,icon, dbname="./onion_data.db"):
    if url==base_url:return
    conn = sqlite3.connect(dbname)
    cur = conn.cursor()
    cur.execute('INSERT OR REPLACE INTO site(url, title, description, icon) VALUES(?,?,?,?)', (url, title, description,icon))
    conn.commit()
    cur.close()
    conn.close()

def search_sql(url):
    conn = sqlite3.connect("./onion_data.db")
    cur = conn.cursor()
    r=cur.execute("SELECT EXISTS(SELECT 1 FROM site WHERE url = ?)", (url,))
    result = cur.fetchone()[0]
    if result==True:
        return_="find"
    else:
        return_="err"
    cur.close()
    conn.close()
    return return_

def html_parse(content, url):
    url_list = []
    title = "Untitle"
    description = "null"
    icon=""
    if re.search("<title>",content) and re.search("</title>",content):
        title = content.split("</title>")[0].split("<title>")[1]
    if re.search('name="description"',content):
        description = content.split('name="description"')[1].split('"')[1]
    if re.search('<link rel="icon" href=',content):
        icon=content.split('<link rel="icon" href=')[1].split('"')[1]
        if not url.startswith('http://') and not url.startswith('https://') and not url.startswith("//"):icon="http://"+icon
    url_template = re.compile(r"http://[A-Za-z0-9.]+\.onion")
    for mat in url_template.finditer(content):
        if mat.group() not in url_list:
            url_list.append(mat.group())
    print(f"Title: {title} Description: {description} URL: {url} {len(url_list)} urls found.")
    add_sql(url,title, description,icon)
    return url_list

async def get_request():
    start_url = base_url
    session=httpx.AsyncClient(proxy="socks5://localhost:9050",follow_redirects=True)
    try:
        response = await session.get("https://httpbin.org/ip")
        print("[*] TorIP: "+response.json()["origin"])
    except:
        print(f"[!] Please run tor")
        return
    url_list1 = await onion_get_request(start_url, session)
    if not url_list1:
        return
    url_list2 = []
    url_list1.pop(0)
    while True:
        urls = [url_list1[i:i+70] for i in range(0, len(url_list1), 70)]
        for url_list in urls:
            result=await asyncio.gather(*[gather(url,session) for url in url_list],return_exceptions=True)
            for get_result in result:
                for urls in get_result:
                    if urls not in url_list2:
                        url_list2.append(urls)
        url_list1 = []
        urls = [url_list2[i:i+70] for i in range(0, len(url_list2), 70)]
        for url_list in urls:
            result=await asyncio.gather(*[gather(url,session) for url in url_list],return_exceptions=True)
            for get_result in result:
                for urls in get_result:
                    if urls not in url_list1:
                        url_list1.append(urls)
        url_list2 = []
        if len(url_list1) == 0 and len(url_list2) == 0:
            break
    await get_request()

async def gather(url,session):
    print(f"[*] Accessing: {url}")
    return await onion_get_request(url,session)
    

async def onion_get_request(url, session):
    url_list = []
    if url!=base_url:
        if search_sql(url) == "find":
            return url_list
    headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8", "Accept-Encoding": "gzip, deflate","Accept-Language": "ja","Upgrade-Insecure-Requests": "1", "User-Agent": "Mozilla/5.0 (Android 10; Mobile; rv:109.0) Gecko/115.0 Firefox/115.0"}
    try:
        response = await session.get(url, headers=headers, timeout=20)
        url_list = html_parse(response.text, url)
    except:
        print(f"[!] Failed: {url}")
   
    print("============================================================================================")
    return url_list

async def main():
    with sqlite3.connect("./onion_data.db") as db:
        cur = db.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS site(url STRING, title STRING, description STRING, icon STRING)")
        db.commit()
    await get_request()

asyncio.run(main())
