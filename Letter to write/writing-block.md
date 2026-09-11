IMD API ACCESS APPLICATION — SKYGUARD AI

1. Briefly introduce your company or organization.

We are a student project team from [Full Institute Name], [Department/Programme], located in [City, State]. We are developing SkyGuard AI, a software-based weather-observation quality-control prototype aligned with the requirements of SIH problem statement 26073, “AI/ML-Based Intelligent Anomaly Detection for Automatic Weather Stations.”

Our team has experience in Python, machine learning, time-series analysis, data processing, backend development and web dashboards. The project aims to identify potentially faulty weather observations while distinguishing them from genuine meteorological changes.

The applicant and project contact is [Full Name], [Student ID], working under the guidance of [Faculty Mentor Name and Designation]. We request IMD API access for academic development, evaluation and demonstration of this project.


2. Is your organization generating any revenue through the use of these APIs? Please provide a declaration.

This application concerns a non-commercial student academic project. The project does not currently generate revenue from IMD APIs or IMD data. We do not propose to sell the data, provide paid API access, operate a subscription service, or monetize the proposed demonstration.

The requested access will be used for academic research, prototype development, testing and educational demonstrations, subject to IMD’s applicable access and usage conditions.

Any future proposal for commercial use or wider redistribution will be submitted to IMD for the necessary authorization before such use begins.


3. How will your organization acknowledge the India Meteorological Department when sharing this data with your users?

We will prominently acknowledge the India Meteorological Department wherever IMD observations are displayed or used in permitted reports, presentations and demonstrations.

The proposed acknowledgement is:

“Source: India Meteorological Department (IMD), Ministry of Earth Sciences, Government of India.”

Where practical, we will also display the source API, station identifier, observation timestamp and retrieval timestamp, and provide a link to the official IMD website.

SkyGuard-generated anomaly flags, confidence estimates, suggested corrections and sensor-health indicators will be clearly identified as experimental outputs produced by our project. They will not be represented as IMD-issued warnings, verified equipment diagnoses, or IMD-endorsed findings.

Original observations will remain distinguishable from derived estimates. Any use of IMD branding or logos will follow the permissions and conditions specified by IMD.


4. How will you disseminate information obtained from these APIs to your users?

The initial audience will be our project team, faculty supervisor, institutional reviewers and competition evaluators. Information will be presented through an academic web dashboard showing station observations, observation timestamps, data freshness, time-series charts and experimental anomaly-detection outputs.

We propose to use limited examples and aggregate findings in academic reports and presentations, subject to IMD’s permitted usage conditions. For an offline demonstration, we request permission to retain and replay a limited, timestamped sample of observations with clear attribution and historical-replay labelling.

We will not publish API credentials or offer unrestricted access to raw IMD datasets. Public display, redistribution, downloadable observation records and data retention will follow the scope explicitly permitted by IMD.

The prototype will be presented as an academic decision-support system and will not issue operational public safety or aviation advisories.


Project Description

Project title: SkyGuard AI — Intelligent Anomaly Detection for Automatic Weather Station Observations

SkyGuard AI is a software prototype being developed against the requirements of SIH problem statement 26073. Its objective is to identify abnormal, inconsistent or potentially faulty weather-station readings using temperature, atmospheric pressure and relative humidity, while reducing false alarms during genuine meteorological events.

The current project includes historical-data processing, controlled sensor-fault simulation, statistical quality checks, machine-learning experiments, an offline replay system and a web dashboard. Historical NOAA/NCEI and DWD observations have supported development. We now seek official IMD observations to implement and evaluate an Indian AWS ingestion pathway.

We request access primarily to:
• AWS/ARG Data: https://api.imd.gov.in/api/v1/aws_data
• AWS Mapping Data: https://api.imd.gov.in/api/v1/aws_data_mapping

If available and separately authorized, the Current Weather API would provide a supplementary observation source:
https://api.imd.gov.in/api/v1/current_wx

The required information comprises temperature, relative humidity, pressure, observation date/time, station identity and available station metadata. We will preserve the distinction between mean sea-level pressure and station pressure and confirm timestamp conventions, missing-value codes and reporting intervals before integration. Records without the required parameters will be handled explicitly rather than populated with invented measurements.

Historical data will be used for model development. Incoming observations will be processed using the trained model and the station’s available past observations. Methods include physical and temporal quality checks, robust rolling statistics, slope and persistence features, gradient-boosted classification and neighbour consistency where suitable observations are available.

Outputs will include experimental anomaly alerts, severity, calibrated confidence where validated, probable fault categories, explanations and advisory sensor-health indicators. Optional corrected-value estimates will preserve the original observation and disclose uncertainty. Maintenance guidance will be identified as heuristic unless independently validated.

The proposed initial pilot covers selected stations around Delhi, Telangana, Karnataka and Tamil Nadu, followed by additional regions if authorized. We request guidance on permitted polling frequency, request limits, storage, redistribution and availability of historical observations. Access to current observations alone will not be treated as providing confirmed sensor-failure labels.

The project requires no purchase or installation of station hardware. Its purpose is academic research and demonstration of a scalable software approach to weather-observation quality control.