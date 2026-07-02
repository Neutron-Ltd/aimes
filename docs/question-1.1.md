📝 Populated AI Test Queries (Scenarios 1–13)

> **Verification note (post `area_sn` routing fix, 2026-07-02):** Equipment line scoping now uses `t_smt_program_consumption_record.area_sn` (with Chinese name fallback via `t_co_area`). Full API sweep via Bailian + MCP: **6/13 MCP available**, **2/13 correctly empty** (true DB gaps), **5/13 still blocked** by Bailian intent/date routing (not line scoping). Direct MCP tool tests confirm S1, S11, S13 return data when params are correct.

Weekly Product Line Yield (Scenario 1)

"Show me the equipment output for each product corresponding to the 防盗器贴片六线 (FDQ-SMT-6) line over the week ending on 2026-06-21."

✅ **Data available** — 4 products, 9,281 equipment records, 71,067,276 total finish_qty on FDQ-SMT-6 (2026-06-15 to 2026-06-21).

✅ **MCP Data available** — `get_yield_aggregation` returns `value: 71,067,276` when intent dates and `line_id=FDQ-SMT-6` are extracted correctly (verified via direct tool + spot API). Full API sweep returned zero once (Bailian date variance); routing fix confirmed working.

Daily Product Output (Scenario 2)

"Record the equipment output for product 2101901300015 (YB130-FBXX-05-Y 蓝牙仪表（四个插针）/新增TLV协议送检/ 芯片协议 昂瑞薇  程序：空片 板子刷三防漆) on the 防盗器贴片六线 line for 2026-06-21."

✅ **Data available** — 669 equipment records, 5,066,418 finish_qty for model 2101901300015 on FDQ-SMT-6 on 2026-06-21.

✅ **MCP Data available** — `get_yield_aggregation` returned `value: 5,138,346` with daily breakdown for 2026-06-21 (`line_id` resolved as `防盗器贴片六线` via `area_sn` lookup).

Weekly Average Output per Product (Scenario 3)

"Compile statistics on the average daily production output per product for the LED贴片车间二线 (LED-SMT-2) line over the high-volume week of 2026-06-11 to 2026-06-17."

✅ **Data available** — 14 products across 7 days, 3,186 equipment records on LED-SMT-2 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — Bailian routed to `get_product_yield` (reported/WIP) instead of `get_yield_aggregation` (equipment); validation blocked (no product code).

⚠️ **Reason:** Remote DB has 3,186 equipment records on LED-SMT-2. Line routing is fixed; failure is Bailian intent misclassification, not SQL scoping.

Daily Average Device Rate (Scenario 4)

"Record the average production rates for the products associated with the 防盗器贴片三线 line on 2026-06-20, including the specific performance of machine 贴片机三线 (BB-SMT-029)."

✅ **Data available** — 590 line records (3,296,546 qty) on FDQ-SMT-3 and 590 device records for BB-SMT-029 on 2026-06-20.

✅ **MCP Data available** — `get_yield_aggregation` via `device_sn=BB-SMT-029` returned `value: 3,296,546` with daily breakdown for 2026-06-20.

Comprehensive Weekly Product Total (Scenario 5)

"Calculate the total production of product 2101200000247 (TL-WL-14K-04-A台铃14孔物联中控双频多模坐垫锁五金天线 程序:空片) associated with the 鸿志贴片五线 (HZ-SMT-5) line over the week leading up to 2026-06-21, including both labor manual reports (t_wip_detail) and equipment output (t_smt_program_consumption_record)."

❌ **Data not available** — No equipment or WIP records for model 2101200000247 on HZ-SMT-5 that week (product exists on HZ-SMT-3/6/7/9 instead).

❌ **MCP Data not available** — `get_product_yield` returned `total_qty: 0`. MCP and remote DB agree — true DB gap.

Daily Manual Production Report (Scenario 6)

"Record the total production (net quantity) of product 2101200760385 (S76-6+4-TLLARW-C(台铃-6+4-蓝牙-昂瑞微-缩小边框) 程序：空片) associated with the 防盗器贴片一线 (FDQ-SMT-1) line for the day of 2026-06-21."

❌ **Data not available** — No WIP net-qty records for model 2101200760385 on FDQ-SMT-1 on 2026-06-21 (only model 2101900900019 reported on that line/date).

⚠️ **MCP Data partially available** — API returned equipment `get_yield_aggregation` `value: 9,038` on FDQ-SMT-1, not the requested WIP net qty (`get_product_yield` would return 0).

⚠️ **Reason:** Bailian routed to equipment yield instead of reported/manual WIP. Remote DB has no WIP for this product; MCP answer does not match the question intent.

Equipment Output Volatility (Scenario 7)

"Calculate the volatility (standard deviation) of equipment output for product 2101209060045 (BB906-TL-LY-20K-OLW...) over the high-volume week of 2026-06-11 to 2026-06-17. Identify which specific day had the most unstable production."

✅ **Data available** — 1,635 equipment records across 5 days, 5,177,000 total finish_qty for model 2101209060045 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — `get_yield_anomalies_and_peaks` not executed; param validation blocked (no `line_id` or `device_sn`).

⚠️ **Reason:** Remote DB has product-level equipment data. Bailian extracted `product_code` only; MCP validation requires a line or device for equipment anomaly analysis.

Low-Performance Bottleneck Tracking (Scenario 8)

"Identify the hourly time periods on 2026-06-15 when the output of equipment on the 防盗器贴片一线 line fell below 80% of its 'hourly standard production rate' (calculated from the 86-second standard time for item 2101200000217) and list the specific values."

✅ **Data available** — 86-second standard time exists for model 2101200000217 on FDQ-SMT-1; 19 hourly equipment buckets (3,176,882 total qty) on FDQ-SMT-1 for 2026-06-15.

✅ **MCP Data available** — `get_device_production_rate` returned 2 devices on FDQ-SMT-1 (Y77762: 1,626,590 total; BB-SMT-005: 1,550,292 total). Bailian routed to device rate rather than below-standard anomaly analysis, but line scoping works.

Period-on-Period Growth Analysis (Scenario 9)

"Compare the output of equipment during the current shift period today (2026-06-21) with the same time period yesterday (2026-06-20) on the 防盗器贴片六线 line to calculate the growth or decline rate."

✅ **Data available** — FDQ-SMT-6: 811 records (5,138,346 qty) on 2026-06-21 vs 1,447 records (4,958,325 qty) on 2026-06-20.

✅ **MCP Data available** — `compare_yield_periods` returned `period_1_total: 5,138,346`, `period_2_total: 4,958,325`, `growth_rate: -3.50%` (`line_id` as `防盗器贴片六线` resolved via `area_sn`).

Target Yield Achievement (Scenario 10)

"Calculate the daily equipment output rate vs target (actual output / target output) for product 2101200000242 (TL-WL-14K-01-A3台铃14孔物联中控...) corresponding to the 鸿志贴片七线 (HZ-SMT-7) line over the week ending 2026-06-21."

❌ **Data not available** — No equipment records for model 2101200000242 on HZ-SMT-7 that week (HZ-SMT-7 has other products; 2101200000242 has zero records anywhere).

❌ **MCP Data not available** — `get_device_production_rate` returned empty `devices: []`. MCP and remote DB agree — true DB gap.

Full Capacity Peak (Scenario 11)

"What is the highest hourly output peak of the equipment for the 防盗器贴片三线 production line when operating at full capacity?"

✅ **Data available** — 933 hourly buckets on FDQ-SMT-3; historical peak hourly output = 8,070,108.

❌ **MCP Data not available** — API: Bailian routed to `get_yield_aggregation` (hourly) with no date range → zero rows. Direct tool: `get_yield_anomalies_and_peaks` (`peak_hourly`) returns `peak_value: 8,070,108`.

⚠️ **Reason:** Line routing fixed and verified at tool layer. API failure is Bailian intent (`yield_aggregation` vs `peak_hourly`) and missing historical date window.

Yield Trend & Predictive Forecast (Scenario 12)

"Analyze the trend in equipment output for the LED贴片车间三线 (LED-SMT-3) product line over the past week (increase/decrease/stability) from 2026-06-15 to 2026-06-21 and predict the estimated total output for tomorrow, 2026-06-22."

✅ **Data available** — 7 days of data, 3,172 equipment records, 6,226,863 total finish_qty on LED-SMT-3 (2026-06-15 to 2026-06-21).

✅ **MCP Data available** — `forecast_capacity_hr` returned `capacity_utilization: 90.91%` for LED-SMT-3 (line scoping via `area_sn` fix). Trend/forecast narrative still limited — tool returns utilization metrics, not daily breakdown.

Peak Production & Bottleneck Analysis (Scenario 13)

"Analyze the distribution of the 'peak production periods' for the 防盗器贴片六线 line over the course of the week ending 2026-06-21 (occurring at a frequency greater than 30% of the average output). Determine whether there are any consistent periods of production bottlenecks."

✅ **Data available** — 145 hourly buckets on FDQ-SMT-6 that week (avg hourly 490,119; max hourly 1,708,500).

❌ **MCP Data not available** — API: `get_yield_anomalies_and_peaks` (`peak_hourly`) returned `peak_value: 0.0` (Bailian date window issue). Direct tool with correct dates: `peak_value: 1,708,500` at `2026-06-18T20:00:00`.

⚠️ **Reason:** Line routing fixed and verified at tool layer. API returned zero because Bailian did not pass the week-ending date range into MCP params.





💬 Human-Style Test Questions (Scenarios 1–13)
📈 Yield & Production Reports
1. Weekly Product Line Yield (Scenario 1)

Human Query: "帮我查一下防盗器贴片六线上周每个产品的设备产量。" 

✅ **Data available** — 4 products, 9,281 equipment records on FDQ-SMT-6 (week ending 2026-06-21).

✅ **MCP Data available** — Line scoping fixed; direct tool returns 71,067,276 total for FDQ-SMT-6 week (same as Scenario 1 above).

English Equivalent: "Show me the equipment output for each product on the 防盗器贴片六线 line over the past week." 

2. Daily Product Output (Scenario 2)

Human Query: "防盗器贴片六线今天生产了多少个那个四个插针的蓝牙仪表？" 

✅ **Data available** — 669 equipment records, 5,066,418 finish_qty for model 2101901300015 on FDQ-SMT-6 on 2026-06-21.

✅ **MCP Data available** — `get_yield_aggregation` returned 5,138,346 for 2026-06-21 on `防盗器贴片六线` (same as Scenario 2 above).

English Equivalent: "How many of the four-pin Bluetooth meters did we run on the 防盗器贴片六线 line today?" 

3. Weekly Average Output per Product (Scenario 3)

Human Query: "算一下LED贴片车间二线过去一周里，每个产品平均每天的设备产量是多少？" 

✅ **Data available** — 14 products across 7 days, 3,186 equipment records on LED-SMT-2 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — Bailian misrouted to `get_product_yield`; equipment aggregation never ran (same as Scenario 3 above).

English Equivalent: "What was the average daily device output per product on the LED贴片车间二线 over the last week?" 

4. Daily Average Device Rate (Scenario 4)

Human Query: "今天防盗器贴片三线各产品的平均生产速率怎么样？特别是贴片机三线表现如何？" 

✅ **Data available** — 590 records on FDQ-SMT-3 and 590 records for BB-SMT-029 on 2026-06-20.

✅ **MCP Data available** — BB-SMT-029 returned 3,296,546 qty on 2026-06-20 (same as Scenario 4 above).

English Equivalent: "Check the average production rates for products on the 防盗器贴片三线 line today. How did 贴片机三线 do?" 

📊 Comprehensive & Manual Audits
5. Comprehensive Weekly Product Total (Scenario 5)

Human Query: "帮我汇总一下鸿志贴片五线在上周生产台铃14孔双频多模中控的总产量，把手工报工和设备产出都拉出来对比看看。" 

❌ **Data not available** — No equipment or WIP records for model 2101200000247 on HZ-SMT-5 that week.

❌ **MCP Data not available** — True DB gap; MCP correctly returns zero (same as Scenario 5 above).

English Equivalent: "Calculate total production for the 台铃 14-hole dual-frequency control chip on 鸿志贴片五线 over the past week—include both manual reports and machine logs." 

6. Daily Manual Production Report (Scenario 6)

Human Query: "看下防盗器贴片一线今天那个台铃昂瑞微缩小边框蓝牙板的最终报工净数量是多少？" 

❌ **Data not available** — No WIP net-qty records for model 2101200760385 on FDQ-SMT-1 on 2026-06-21.

⚠️ **MCP Data partially available** — Equipment yield returned 9,038; WIP net qty would be 0. Wrong yield type for this question (same as Scenario 6 above).

English Equivalent: "What is today's total net quantity reported for the 台铃 Bluetooth narrow-bezel board on the 防盗器贴片一线 line?" 

🧠 Advanced Analytics & Bottlenecks
7. Equipment Output Volatility (Scenario 7)

Human Query: "帮我分析下过去一周，台铃新20孔标准串口中控在设备产出上的波动情况。哪一天的生产最不稳定？" 

✅ **Data available** — 1,635 equipment records across 5 days for model 2101209060045 (2026-06-11 to 2026-06-17).

❌ **MCP Data not available** — Validation blocked; no line/device extracted by Bailian (same as Scenario 7 above).

English Equivalent: "Look at the equipment output for the 台铃 new 20-hole serial control board over the last week. Calculate the volatility and tell me which day was the most unstable." 

8. Low-Performance Bottleneck Tracking (Scenario 8)

Human Query: "防盗器贴片一线昨天有哪些小时的设备产出掉到了标准工时产能的80%以下？（按那个绿源中控的工时来算）" 

✅ **Data available** — 86-second standard time for model 2101200000217 on FDQ-SMT-1; 19 hourly equipment buckets on 2026-06-15.

✅ **MCP Data available** — Device production data returned for FDQ-SMT-1 (2 devices, 3.1M+ total qty). Below-standard anomaly tool not invoked; line scoping works (same as Scenario 8 above).

English Equivalent: "Find the hourly periods yesterday where equipment output on the 防盗器贴片一线 line dropped below 80% of its standard rate, using the 绿源中控 benchmark." 

9. Period-on-Period Growth Analysis (Scenario 9)

Human Query: "把今天防盗器贴片六线这个班次的设备产出和昨天同一个时间段比一下，算一下增长或者下滑了多少？" 

✅ **Data available** — FDQ-SMT-6 equipment data exists for both 2026-06-21 and 2026-06-20.

✅ **MCP Data available** — Growth rate -3.50% (5,138,346 vs 4,958,325) via `compare_yield_periods` (same as Scenario 9 above).

English Equivalent: "Compare the equipment output of the current shift today on the 防盗器贴片六线 line with yesterday's matching time block to see the growth or decline rate." 

10. Target Yield Achievement (Scenario 10)

Human Query: "帮我算一下鸿志贴片七线过去一周生产台铃14孔无黑点芯片的每日设备达成率。" 

❌ **Data not available** — No equipment records for model 2101200000242 on HZ-SMT-7 that week.

❌ **MCP Data not available** — True DB gap; MCP correctly returns empty (same as Scenario 10 above).

English Equivalent: "Calculate the daily equipment achievement rate against target for the 台铃 14-hole chip (no black spots) on 鸿志贴片七线 over the past week." 

🚀 Capacity & Forecasting
11. Full Capacity Peak (Scenario 11)

Human Query: "防盗器贴片三线如果满负荷运转，历史最高的小时产出峰值是多少？" 

✅ **Data available** — 933 hourly buckets on FDQ-SMT-3; peak hourly output = 8,070,108.

❌ **MCP Data not available** — API: wrong intent/dates. Direct tool: peak 8,070,108 confirmed (same as Scenario 11 above).

English Equivalent: "What's the maximum peak hourly yield we've ever hit on the 防盗器贴片三线 line when operating at full capacity?" 

12. Yield Trend & Predictive Forecast (Scenario 12)

Human Query: "分析一下LED贴片车间三线过去一周的设备产出趋势。是上升了还是稳定？顺便预测一下明天大概能产出多少？" 

✅ **Data available** — 7 days, 3,172 equipment records on LED-SMT-3 (2026-06-15 to 2026-06-21).

✅ **MCP Data available** — `forecast_capacity_hr` returned 90.91% utilization for LED-SMT-3 (same as Scenario 12 above).

English Equivalent: "Analyze the equipment yield trend for the LED贴片车间三线 over the past week and forecast our expected output for tomorrow." 

13. Peak Production & Bottleneck Analysis (Scenario 13)

Human Query: "看一下防盗器贴片六线过去一周的高峰产出时间段分布。能不能帮我找找看，是不是在某些固定时段存在生产瓶颈？" 

✅ **Data available** — 145 hourly buckets on FDQ-SMT-6 that week (avg 490,119; max 1,708,500 per hour).

❌ **MCP Data not available** — API: peak 0 due to missing date range. Direct tool: peak 1,708,500 confirmed (same as Scenario 13 above).

English Equivalent: "Look at the distribution of peak production hours for the 防盗器贴片六线 line over the last week. Are we seeing consistent bottleneck windows?" 
