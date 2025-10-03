from prometheus_api_client import PrometheusConnect
import matplotlib.pyplot as plt
import io


prom = PrometheusConnect(url="http://localhost:9090", disable_ssl=True)

metric_data = prom.get_metric_range_data(
    metric_name="up",
    start_time="2023-01-01T00:00:00Z",
    end_time="2023-01-02T00:00:00Z",
)

plt.figure(figsize=(10, 5))
for metric in metric_data:
    plt.plot(
        [x[0] for x in metric["values"]],
        [x[1] for x in metric["values"]],
        label=metric["metric"].get("instance", "N/A"),
    )
plt.title("Prometheus Metric: up")
plt.xlabel("Time")
plt.ylabel("Value")
plt.legend()

buf = io.BytesIO()
plt.savefig(buf, format="png")
buf.seek(0)
plt.close()
