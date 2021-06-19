db = new Mongo().getDB("spiderDB");

db.createCollection('test', { capped: false });
db.createCollection('jobs', { capped: false });

db.test.insert([
    { "url": {"url": "http://www.baidu.com", "domain": "baidu.com"}, "html": "<p>foo</p>", "create_dt": "202105271900", "job_id": "1", "keywords":[]},
    { "url": {"url": "http://www.news.com", "domain": "news.com"},  "html": "<p>news</p>", "create_dt": "202105271901", "job_id": "1", "keywords":[]},
    { "url": {"url": "http://www.nytimes.com", "domain": "nytimes.com"},  "html": "<p>breaking news</p>", "create_dt": "202105271902", "job_id": "1", "keywords":[]},
    { "url": {"url": "http://www.washintonpost.com", "domain": "washintonpost.com"},  "html": "<p>usa</p>", "create_dt": "202105271902", "job_id": "1", "keywords":[]},
]);
