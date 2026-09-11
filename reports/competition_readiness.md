# SkyGuard competition-readiness profile

The benchmark covers the complete deployed three-parameter Phase 10 scoring path, not only SQLite replay.

| Measure | Result |
|---|---:|
| Rows | 400 |
| Full-inference throughput | 204.70 rows/s |
| Mean wall latency | 4.885 ms/row |
| CPU cost | 10.977 CPU-s/1,000 rows |
| Peak traced Python allocation | 6.53 MiB |
| Deployed detector + climatology | 5.20 MiB |

At a 30-minute cadence, 10,000 stations produce about 5.56 readings/s. The measured single-process batch throughput is 36.8 times that arrival rate. This is a capacity projection, not a distributed load test.

Energy is reported honestly through CPU-time and artifact-size proxies. No joule or ESP32 battery claim is made without calibrated hardware measurement.
