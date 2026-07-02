📝 Populated AI Test Queries (Scenarios 1–13)
Weekly Product Line Yield (Scenario 1)

"Show me the equipment output for each product corresponding to the 防盗器贴片六线 (FDQ-SMT-6) line over the week ending on 2026-06-21."

✅ **Data available** — 4 products, 9,281 equipment records, 71,067,276 total finish_qty on FDQ-SMT-6 (2026-06-15 to 2026-06-21).

❌ **MCP Data not available** — `get_yield_aggregation` returned `value: 0`, empty breakdown.

⚠️ **Reason:** Remote DB has 9,281 records for FDQ-SMT-6, but MCP equipment routing filters via `t_co_device.cd_location`, which is `NULL` for line devices (e.g. BB-SMT-072/073). Records are keyed by `area_sn` on `t_smt_program_consumption_record` instead. Bailian intent + synthesis ran correctly; the MCP SQL path returns zero rows.

Daily Product Output (Scenario 2)

"Record the equipment output for product 2101901300015 (YB130-FBXX-05-Y 蓝牙仪表（四个插针）/新增TLV协议送检/ 芯片协议 昂瑞薇  程序：空片 板子刷三防漆) on the 防盗器贴片六线 line for 2026-06-21."

✅ **Data available** — 669 equipment records, 5,066,418 finish_qty for model 2101901300015 on FDQ-SMT-6 on 2026-06-21.

❌ **MCP Data not available** — `get_yield_aggregation` returned `value: 0`, empty breakdown.

⚠️ **Reason:** Remote DB has 669 records (5,066,418 qty) for this product/line/date. Bailian extracted `line_id` as the Chinese name `防盗器贴片六线` (not `FDQ-SMT-6`), and MCP equipment scope still uses `cd_location` (NULL on devices), so the tool query returned zero despite valid remote data.

Weekly Average Output per Product (Scenario 3)

"Compile statistics on the average daily production output per product for the LED贴片车间二线 (LED-SMT-2) line over the high-volume week of 2026-06-11 to 2026-06-17."

✅ **Data available** — 14 products across 7 days, 3,186 equipment records on LED-SMT-2 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — `get_yield_aggregation` returned `value: 0`, empty breakdown.

⚠️ **Reason:** Remote DB has 3,186 records across 7 days on LED-SMT-2. MCP `get_yield_aggregation` (equipment) uses `cd_location` device lookup, which matches no devices; Bailian synthesis then reported zero output from the empty MCP payload.

Daily Average Device Rate (Scenario 4)

"Record the average production rates for the products associated with the 防盗器贴片三线 line on 2026-06-20, including the specific performance of machine 贴片机三线 (BB-SMT-029)."

✅ **Data available** — 590 line records (3,296,546 qty) on FDQ-SMT-3 and 590 device records for BB-SMT-029 on 2026-06-20.

✅ **MCP Data available** — `get_yield_aggregation` via `device_sn=BB-SMT-029` returned `value: 3,296,546` with daily breakdown for 2026-06-20. Bailian synthesis produced a valid report.

Comprehensive Weekly Product Total (Scenario 5)

"Calculate the total production of product 2101200000247 (TL-WL-14K-04-A台铃14孔物联中控双频多模坐垫锁五金天线 程序:空片) associated with the 鸿志贴片五线 (HZ-SMT-5) line over the week leading up to 2026-06-21, including both labor manual reports (t_wip_detail) and equipment output (t_smt_program_consumption_record)."

❌ **Data not available** — No equipment or WIP records for model 2101200000247 on HZ-SMT-5 that week (product exists on HZ-SMT-3/6/7/9 instead).

❌ **MCP Data not available** — `get_product_yield` returned `total_qty: 0`, empty breakdown. Bailian correctly reported no production; remote DB also has no matching rows for this line/product combination.

Daily Manual Production Report (Scenario 6)

"Record the total production (net quantity) of product 2101200760385 (S76-6+4-TLLARW-C(台铃-6+4-蓝牙-昂瑞微-缩小边框) 程序：空片) associated with the 防盗器贴片一线 (FDQ-SMT-1) line for the day of 2026-06-21."

❌ **Data not available** — No WIP net-qty records for model 2101200760385 on FDQ-SMT-1 on 2026-06-21 (only model 2101900900019 reported on that line/date).

❌ **MCP Data not available** — `get_product_yield` returned `total_qty: 0`. MCP and remote DB agree — no WIP data for this product/line/date.

Equipment Output Volatility (Scenario 7)

"Calculate the volatility (standard deviation) of equipment output for product 2101209060045 (BB906-TL-LY-20K-OLW...) over the high-volume week of 2026-06-11 to 2026-06-17. Identify which specific day had the most unstable production."

✅ **Data available** — 1,635 equipment records across 5 days, 5,177,000 total finish_qty for model 2101209060045 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — `get_yield_anomalies_and_peaks` was not executed; param validation blocked the call.

⚠️ **Reason:** Remote DB has 1,635 equipment records for model 2101209060045. Bailian classified intent as `yield_anomalies` but did not extract `line_id` or `device_sn` (only `product_code`). MCP validation requires a line or device for equipment analysis, so the tool never ran despite product-level data existing in the remote DB.

Low-Performance Bottleneck Tracking (Scenario 8)

"Identify the hourly time periods on 2026-06-15 when the output of equipment on the 防盗器贴片一线 line fell below 80% of its 'hourly standard production rate' (calculated from the 86-second standard time for item 2101200000217) and list the specific values."

✅ **Data available** — 86-second standard time exists for model 2101200000217 on FDQ-SMT-1; 19 hourly equipment buckets (3,176,882 total qty) on FDQ-SMT-1 for 2026-06-15.

❌ **MCP Data not available** — `get_yield_anomalies_and_peaks` blocked by param validation (`line_id` not accepted as a valid production line ID).

⚠️ **Reason:** Remote DB has 19 hourly equipment buckets on FDQ-SMT-1 for 2026-06-15 plus the 86s standard-time row. Bailian extracted `line_id` as Chinese `防盗器贴片一线` instead of `FDQ-SMT-1`; MCP validation rejected it and never queried the DB. Even when intent passes, equipment routing via `cd_location` would still return zero.

Period-on-Period Growth Analysis (Scenario 9)

"Compare the output of equipment during the current shift period today (2026-06-21) with the same time period yesterday (2026-06-20) on the 防盗器贴片六线 line to calculate the growth or decline rate."

✅ **Data available** — FDQ-SMT-6: 811 records (5,138,346 qty) on 2026-06-21 vs 1,447 records (4,958,325 qty) on 2026-06-20.

❌ **MCP Data not available** — `compare_yield_periods` returned `period_1_total: 0`, `period_2_total: 0`, `growth_rate: null`.

⚠️ **Reason:** Remote DB has substantial equipment output on both dates for FDQ-SMT-6. Bailian extracted `line_id` as `防盗器贴片六线` (Chinese name), and MCP equipment comparison uses `cd_location` device lookup (NULL on devices), yielding zero totals for both periods.

Target Yield Achievement (Scenario 10)

"Calculate the daily equipment output rate vs target (actual output / target output) for product 2101200000242 (TL-WL-14K-01-A3台铃14孔物联中控...) corresponding to the 鸿志贴片七线 (HZ-SMT-7) line over the week ending 2026-06-21."

❌ **Data not available** — No equipment records for model 2101200000242 on HZ-SMT-7 that week (HZ-SMT-7 has other products; 2101200000242 has zero records anywhere).

❌ **MCP Data not available** — `get_device_production_rate` returned empty `devices: []`. MCP and remote DB agree — no records for this product/line.

Full Capacity Peak (Scenario 11)

"What is the highest hourly output peak of the equipment for the 防盗器贴片三线 production line when operating at full capacity?"

✅ **Data available** — 933 hourly buckets on FDQ-SMT-3; historical peak hourly output = 8,070,108.

❌ **MCP Data not available** — `get_yield_anomalies_and_peaks` blocked by param validation (no accepted `line_id` or `device_sn`).

⚠️ **Reason:** Remote DB has 933 hourly buckets on FDQ-SMT-3 with peak 8,070,108. Bailian did not extract `FDQ-SMT-3` or a device SN into structured params, so MCP validation stopped execution before querying the remote DB.

Yield Trend & Predictive Forecast (Scenario 12)

"Analyze the trend in equipment output for the LED贴片车间三线 (LED-SMT-3) product line over the past week (increase/decrease/stability) from 2026-06-15 to 2026-06-21 and predict the estimated total output for tomorrow, 2026-06-22."

✅ **Data available** — 7 days of data, 3,172 equipment records, 6,226,863 total finish_qty on LED-SMT-3 (2026-06-15 to 2026-06-21).

❌ **MCP Data not available** — First API run: Bailian intent call failed (DNS error resolving `dashscope.aliyuncs.com`). Retry: `forecast_capacity_hr` returned `capacity_utilization: 0.0` with no throughput data.

⚠️ **Reason:** Remote DB has 3,172 records (6,226,863 qty) on LED-SMT-3 for the week. Initial failure was a transient Bailian/DashScope network error inside Docker. On retry, Bailian routed to `forecast_capacity_hr`, which also depends on `cd_location` device scoping and returned 0% utilization despite real production data in the remote DB.

Peak Production & Bottleneck Analysis (Scenario 13)

"Analyze the distribution of the 'peak production periods' for the 防盗器贴片六线 line over the course of the week ending 2026-06-21 (occurring at a frequency greater than 30% of the average output). Determine whether there are any consistent periods of production bottlenecks."

✅ **Data available** — 145 hourly buckets on FDQ-SMT-6 that week (avg hourly 490,119; max hourly 1,708,500).

❌ **MCP Data not available** — `get_yield_anomalies_and_peaks` (`peak_hourly`) returned `peak_value: 0.0`, `peak_hour: null`.

⚠️ **Reason:** Remote DB has 145 hourly buckets on FDQ-SMT-6 that week. Bailian extracted `line_id` as `防盗器贴片六线`, and MCP equipment scope via `cd_location` returned no hourly rows, so peak analysis reported zero despite real remote data.





💬 Human-Style Test Questions (Scenarios 1–13)
📈 Yield & Production Reports
1. Weekly Product Line Yield (Scenario 1)

Human Query: "帮我查一下防盗器贴片六线上周每个产品的设备产量。" 

✅ **Data available** — 4 products, 9,281 equipment records on FDQ-SMT-6 (week ending 2026-06-21).

❌ **MCP Data not available** — `get_yield_aggregation` returned zero (same `cd_location` routing gap as Scenario 1 above).

⚠️ **Reason:** Remote DB has data; MCP equipment line filter misses it because devices lack `cd_location` and records live under `area_sn`.

English Equivalent: "Show me the equipment output for each product on the 防盗器贴片六线 line over the past week." 

2. Daily Product Output (Scenario 2)

Human Query: "防盗器贴片六线今天生产了多少个那个四个插针的蓝牙仪表？" 

✅ **Data available** — 669 equipment records, 5,066,418 finish_qty for model 2101901300015 on FDQ-SMT-6 on 2026-06-21.

❌ **MCP Data not available** — `get_yield_aggregation` returned zero (Chinese `line_id` + `cd_location` routing gap).

⚠️ **Reason:** Remote DB has 669 records; MCP returned empty payload for the same routing reasons as Scenario 2 above.

English Equivalent: "How many of the four-pin Bluetooth meters did we run on the 防盗器贴片六线 line today?" 

3. Weekly Average Output per Product (Scenario 3)

Human Query: "算一下LED贴片车间二线过去一周里，每个产品平均每天的设备产量是多少？" 

✅ **Data available** — 14 products across 7 days, 3,186 equipment records on LED-SMT-2 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — `get_yield_aggregation` returned zero (`cd_location` routing gap).

⚠️ **Reason:** Remote DB has 3,186 records on LED-SMT-2; MCP equipment scope returned no rows.

English Equivalent: "What was the average daily device output per product on the LED贴片车间二线 over the last week?" 

4. Daily Average Device Rate (Scenario 4)

Human Query: "今天防盗器贴片三线各产品的平均生产速率怎么样？特别是贴片机三线表现如何？" 

✅ **Data available** — 590 records on FDQ-SMT-3 and 590 records for BB-SMT-029 on 2026-06-20.

✅ **MCP Data available** — Worked when Bailian resolved `device_sn=BB-SMT-029` (3,296,546 qty on 2026-06-20).

English Equivalent: "Check the average production rates for products on the 防盗器贴片三线 line today. How did 贴片机三线 do?" 

📊 Comprehensive & Manual Audits
5. Comprehensive Weekly Product Total (Scenario 5)

Human Query: "帮我汇总一下鸿志贴片五线在上周生产台铃14孔双频多模中控的总产量，把手工报工和设备产出都拉出来对比看看。" 

❌ **Data not available** — No equipment or WIP records for model 2101200000247 on HZ-SMT-5 that week.

❌ **MCP Data not available** — `get_product_yield` returned `total_qty: 0`. True DB gap; MCP result is correct.

English Equivalent: "Calculate total production for the 台铃 14-hole dual-frequency control chip on 鸿志贴片五线 over the past week—include both manual reports and machine logs." 

6. Daily Manual Production Report (Scenario 6)

Human Query: "看下防盗器贴片一线今天那个台铃昂瑞微缩小边框蓝牙板的最终报工净数量是多少？" 

❌ **Data not available** — No WIP net-qty records for model 2101200760385 on FDQ-SMT-1 on 2026-06-21.

❌ **MCP Data not available** — `get_product_yield` returned `total_qty: 0`. True DB gap; MCP result is correct.

English Equivalent: "What is today's total net quantity reported for the 台铃 Bluetooth narrow-bezel board on the 防盗器贴片一线 line?" 

🧠 Advanced Analytics & Bottlenecks
7. Equipment Output Volatility (Scenario 7)

Human Query: "帮我分析下过去一周，台铃新20孔标准串口中控在设备产出上的波动情况。哪一天的生产最不稳定？" 

✅ **Data available** — 1,635 equipment records across 5 days for model 2101209060045 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — Param validation blocked `get_yield_anomalies_and_peaks` (no `line_id`/`device_sn` extracted).

⚠️ **Reason:** Remote DB has product-level equipment data; Bailian did not supply line/device params required by MCP validation.

English Equivalent: "Look at the equipment output for the 台铃 new 20-hole serial control board over the last week. Calculate the volatility and tell me which day was the most unstable." 

8. Low-Performance Bottleneck Tracking (Scenario 8)

Human Query: "防盗器贴片一线昨天有哪些小时的设备产出掉到了标准工时产能的80%以下？（按那个绿源中控的工时来算）" 

✅ **Data available** — 86-second standard time for model 2101200000217 on FDQ-SMT-1; 19 hourly equipment buckets on 2026-06-15.

❌ **MCP Data not available** — Validation blocked or returned zero flagged buckets (Chinese `line_id` + equipment routing gap).

⚠️ **Reason:** Remote DB has hourly equipment data and standard-time baseline; MCP never matched the line correctly and could not surface below-standard hours.

English Equivalent: "Find the hourly periods yesterday where equipment output on the 防盗器贴片一线 line dropped below 80% of its standard rate, using the 绿源中控 benchmark." 

9. Period-on-Period Growth Analysis (Scenario 9)

Human Query: "把今天防盗器贴片六线这个班次的设备产出和昨天同一个时间段比一下，算一下增长或者下滑了多少？" 

✅ **Data available** — FDQ-SMT-6 equipment data exists for both 2026-06-21 and 2026-06-20.

❌ **MCP Data not available** — `compare_yield_periods` returned zero totals for both periods.

⚠️ **Reason:** Remote DB has data on both dates; MCP used Chinese `line_id` and `cd_location` routing, returning `period_1_total: 0`, `period_2_total: 0`.

English Equivalent: "Compare the equipment output of the current shift today on the 防盗器贴片六线 line with yesterday's matching time block to see the growth or decline rate." 

10. Target Yield Achievement (Scenario 10)

Human Query: "帮我算一下鸿志贴片七线过去一周生产台铃14孔无黑点芯片的每日设备达成率。" 

❌ **Data not available** — No equipment records for model 2101200000242 on HZ-SMT-7 that week.

❌ **MCP Data not available** — `get_device_production_rate` returned empty `devices: []`. True DB gap; MCP result is correct.

English Equivalent: "Calculate the daily equipment achievement rate against target for the 台铃 14-hole chip (no black spots) on 鸿志贴片七线 over the past week." 

🚀 Capacity & Forecasting
11. Full Capacity Peak (Scenario 11)

Human Query: "防盗器贴片三线如果满负荷运转，历史最高的小时产出峰值是多少？" 

✅ **Data available** — 933 hourly buckets on FDQ-SMT-3; peak hourly output = 8,070,108.

❌ **MCP Data not available** — Param validation blocked `get_yield_anomalies_and_peaks` (no accepted line/device ID).

⚠️ **Reason:** Remote DB peak is 8,070,108/hr on FDQ-SMT-3; Bailian did not extract `FDQ-SMT-3`, so MCP never executed the peak query.

English Equivalent: "What's the maximum peak hourly yield we've ever hit on the 防盗器贴片三线 line when operating at full capacity?" 

12. Yield Trend & Predictive Forecast (Scenario 12)

Human Query: "分析一下LED贴片车间三线过去一周的设备产出趋势。是上升了还是稳定？顺便预测一下明天大概能产出多少？" 

✅ **Data available** — 7 days, 3,172 equipment records on LED-SMT-3 (2026-06-15 to 2026-06-21).

❌ **MCP Data not available** — Bailian DNS failure on first run; retry routed to `forecast_capacity_hr` with `capacity_utilization: 0.0`.

⚠️ **Reason:** Remote DB has a full week of LED-SMT-3 output; MCP/Bailian either failed to reach DashScope or routed to a capacity tool that returned 0% due to `cd_location` scoping.

English Equivalent: "Analyze the equipment yield trend for the LED贴片车间三线 over the past week and forecast our expected output for tomorrow." 

13. Peak Production & Bottleneck Analysis (Scenario 13)

Human Query: "看一下防盗器贴片六线过去一周的高峰产出时间段分布。能不能帮我找找看，是不是在某些固定时段存在生产瓶颈？" 

✅ **Data available** — 145 hourly buckets on FDQ-SMT-6 that week (avg 490,119; max 1,708,500 per hour).

❌ **MCP Data not available** — `get_yield_anomalies_and_peaks` returned `peak_value: 0.0`.

⚠️ **Reason:** Remote DB has 145 hourly buckets; MCP used Chinese `line_id` and `cd_location` routing, so peak analysis returned empty despite real data.

English Equivalent: "Look at the distribution of peak production hours for the 防盗器贴片六线 line over the last week. Are we seeing consistent bottleneck windows?" 
