# API Documentation

### Endpoints:
**Telelmetry**
- submit telemetry # core collector
- get telemetry history # change to database
- get latest telemetry # post
- get telemetry stats # avg % stats change to database
- register client (testing)

**Client**
- register client
- client heartbeat # seperate from telemetry
- get client info # database
- update client status # req heatbeat
- list_all_clients (testing)

**Alerts**
- submit alert
- submit bulk alerts
- acknowlage alert
- get alert history
- get single alert
- register client for alerts (testing)
--- 
### submit telemery
core endpoint for clients to submit system telemetry and metrics. Clients call this endpoint on a schedule to submit metrics.

This endpoint expects a formatted JSON payload:
```JSON
{
    "CPU_PERCENT": float,
    "MEMORY_PERCENT": <float>,
    "MEMORY_AVAILABLE": <int>,
    "DISK_USAGE": <float>,
    "DISK_READ_BYTES": <int>,
    "DISK_WRITE_BYTES": <int>,
    "NETWORK_SENT_BYTES": <int>,
    "NETWORK_RECV_BYTES": <int>,
    "PROCESS_COUNT": <int>,
    "LOAD_AVERAGE": <lst[float, float, float]> (opt),
    "UPTIME_SECONDS": <int>,
}
```
And will return a response on a the successful processing of the request data. This will follow a standard JSON formatting:

```JSON
{
    "STATUS": <str>,
    "ACK_ID": <str>,
    "RECEIVED_AT": <timestamp>,
    "NEXT_REPORT_IN": <int>,
}
```

After processing this data the data is stored in the client information database table, we keep a `?<90>?` day record of all metrics.<br>
This record is used later in client information charting and used with predictive machine learning algorithums to determin if a client has been compromised or is showing abnormal activity.

### get latest telemetry

Functional endpoint for requesting most recent statistics of the client.<br>\
This endpoint will request the most recent data from the client, the client will then send its data to the core telemetry endpoint and be processed acordingly.

POST to client post head with formatted json.
```JSON
{
    "REQ_TYPE":<str>,
}
```
Each client api endpoint will be a single endpoint that collects and processess all post requests. requests to clients must contain `REQ_TYPE:string` where string is the type of request that has been sent.<br>
e.g. 'Telemetry, heartbeat, update, config'<br>
This will allow us to expose expose as little of the client to the network as possible, minimising client exposure is important for security.<br>\
The client will send back data to the core endpoint and we will force and update for the client data on the web servers cache.

### register client

Interact directly with the api to register a client without interacting with a client device.

This is used for testing and will be removed or hidden in production.
```JSON
{
    "MESSAGE":<str>,
    "CLIENT_ID":<str>,
}
```