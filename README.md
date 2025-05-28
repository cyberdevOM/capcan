# Project CapCan

## What is CapCan
CapCan is a cross platform Honeypot automation tool, It is designed as a Server/Client application that will deploy and report on honeypots distributed 
by the client platforms.

## Project Scope
CapCan Should be able to perform the following tasks:
1. create and distribute dynamic system packages to clients based off of systems needs and operational scope.
2. clients should be able to destribute Predefined HoneyPot Packages to its host system, and detect access to these files.
3. Diferentiate between regular system health checkins and Honeypot alerts.
4. Identify different alerts and provide information to the dashboard in relation to that alert.
5. mask the Process ID of client application to avoid detection by automated tools
6. log incidents in a locally managed centralised database

## Architechtual Design Breakdown
### Server
- **Web Interface (Flask/Django)**:
    - control and conduct deployment of Client processes
    - view alerts, system logs and Client status
    - Perform remote actions on client machines
- **Database (PostgreSQL)**:
    - Collect and store logs
    - alerts and client/system data.
- **Log Ingestion (Logstash/Fluentd)**:
    - Normalise cross platform logs 
    - feed log data into analysis pipelines
- **Security Monitoring (Snort)**:
    - IDS/IPS other basic Security monitoring solutions
- **Alerting (SMTP/API)**:
    - Email SMTP alterts for non critical alerts
    - Teams &/or slack for critical alerts along with dashboard alerts while a user of analyst or higher logged in
- **Visualisation (plotly/dash/matplotlib)**:
    - Graphs on access trends for network and client individual
    - threat heatmaps
    - alert graphs with Severity and risk models

# Author: notdedyet
