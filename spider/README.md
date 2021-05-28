# Spider Service

Request raw data from provided data source.

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
            - If the job is finished, it returns the result
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

2. API
    - DELETE /job/<job_id>
        - cancel a job in progress