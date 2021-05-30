# Spider Service

Request raw data from provided data source.

## How to use this service
1. Scraping static web pages
   1. Send a POST request to /new-job
   2. 
2. Querying scraped contents


## Design Decisions

### Spider Job
1. What is a spider job?
   - A spider job is a scraping task requested by a user. It typically contains a list of urls that need to be scraped.
2. Why do we need to define a spider job?
   - Scraping usually takes quite a while, and users are eager to know the progress. Thus, we need to define the concept of a spider job to present that information.
   - From a user's perspective, a scraping task need to show its current status along with other basic information, e.g. the time that the task is created, the id of the task, the periodicity of the task, and etc.
3. What information a spider job should provide?
   1. Options
      1. Follow the KISS principle: only record the necessary information.
        - some parts of job specification
          - urls
          - job type
        - current status: one of (pending, working, done, failed)
        - progress
          - page crawled
          - time used
        - creation datetime 

### Spider Job Specification
- Describes what kind of task a spider should perform
- It typically includes
  - urls
    - Description: the starting points of a spider job
      - For example, you may want to crawl a e-commerce website on some categories of products
      - You provide the urls of the product pages so the spider can start crawling
  - job type
    - Description: describes what kind of task the spider should perform
      - Internally it is used to create a specialized spider for that task
    - Supported type:
      - basic web page scraping
        - only scrape the provided urls and return the html of those urls
      - search result aggregation
        - perform searches on search engines or general search page and retrieve their results
      - web crawling
        - Start from seed urls, follow all links available. If a sitemap is available, the spider will follow that sitemap.
        - You choose whether the spider should respect the crawling policy. If the spider respects the policy, it will not crawl the urls in robots.txt.
  - scrape rules
    - keyword rules
      - Description: check whether the keyword is in the html content
      - include
      - exclude

    - size limit
      - maximum pages
      - maximum entries
    - time limit
      - past days
      - date before
      - date after
    - regular expression
    - max retry
  - data_collection

## Design

1. Models:
    - HTTPResponse
    - HTMLData
    - DataModel

2. Service:
    - Interfaces:
        - `BaseSpiderService`
            - Description: Defines the common interface for all spider service implementations
            - methods:
                - `async get(data_src: URL) -> HTTPResponse`
                - `async get_many(data_src: List[URL])`
        - `BaseCollectionService`
            - Description: Provides the common interface for accessing data in a collection
            - methods:
                - `async add(data: DataModel)`
                - `async get(query_condition: dict) -> DataModel`
                - `async update(data: DataModel)`
                - `async delete(query_condition: dict)`
        - `BaseJobService`
            - Description: Defines the common interface for all job service implementations
            - methods:
                - `create(job_spec: JobSpecification) -> bool`
                  - create a job
                - `get(job_id: str)`
                  - get a job object by id
                
    - Service Implementations:
        - `HTMLSpiderService`
            - Description
                - Scrape static web page and return its content
            - fields
                - `header: RequestHeader`
                    - `user_agent`
                    - `accept`
                    - `cookie`
                - `html_data_mapper: HTMLDataMapper`
                    - Description: db orm mapping
            - methods:
                - `async get(data_src: URL) -> HTMLData`
                - `async get_many(data_src: List[URL])`
        - `SearchEngineSpiderService`
          - Description
            - A specialized spider that scrapes result pages from a search engine
        - `CollectionService`
            - Description
                - Provide collection data crud methods
                - methods:
                    - `async add(data: DataModel)`
                    - `async get(query_condition: dict) -> DataModel`
                    - `async update(data: DataModel)`
                    - `async delete(query_condition: dict)`

3. API:
    1. GET /html?url=url_string
        - Description: Returns html data from the specified url
        - Returns
            - html: str
                - Description: html string
            - statusCode: int
            - message: str
    2. POST /new-job
        - Description:
            - Add a new scraping job. It only reports whether the job is successfully created
        - Parameters:
            - urls: List[str]
        - Returns:
            - job: Job
                - job_id: str 
                - create_dt: datetime 
                - estimate_time: datetime (TODO)
            - statusCode: int
            - message: str
    3. GET /result/<job_id>
        - Description:
            - Query the job result by job_id
            - If the job is finished, this api returns the result
            - Otherwise it reports its current status (working, failed)
        - Returns:
            - job_result: JobResult
                - job_id: str
                - status: Enum[str]
                    - done
                    - working
                    - failed
                - message: str
                - data: Object
            - statusCode: int
            - message: str
    4. POST /result/new-query
        - Description:
            - Query the job result by query conditions
            - It will only return results from finished jobs
        - Parameters:
            - start_dt: Optional[datetime]
            - end_dt: Optional[datetime]
            - domain: Optional[url]
            - keywords: Optional[List[str]]
            - result_type: Optional[Enum[str]]
                - specify the type of the result
                - currently supported:
                    - webpage
                - future support:
                    - picture
                    - audio
                    - video


## To-do

1. Features
    - Cookie management: manage multiple cookies and automatically refresh them
    - Dynamic web page scraping
    - Multimedia scraping: scrape pictures, videos, and etc.
    - Standalone mode switching
        - Can be configured to be used standalone or orchestrate with other microservices
    - Progress checking
      - Spider will actively reports its job status
    - Spider status: check whether spiders are alive in a distributed system setting.
    - Enhanced Job Specifications
      - Allow specifying the topic of the data
      - Allow storing data with different topics in separate databases
    - AI-driven topic rule
    - Distributed crawler
    - Use bloom filter to search for keywords

2. API
    - DELETE /job/<job_id>
        - cancel a job in progress