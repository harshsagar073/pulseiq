-- PulseIQ Task 5: Workforce dashboard views
-- Exported from the working Task 5 DuckDB database.
-- Re-run scripts/setup_database.py to recreate these views dynamically.

-- View: governed.v_dashboard_current_employee
CREATE VIEW governed.v_dashboard_current_employee AS SELECT CAST(e.employee_id AS VARCHAR) AS employee_id, CAST(e.department_id AS VARCHAR) AS department_id, CAST(e.work_location AS VARCHAR) AS work_location, CAST(e.work_mode AS VARCHAR) AS work_mode FROM raw.dim_employee AS e WHERE ((COALESCE(lower(CAST(e.is_current AS VARCHAR)), '') IN ('y', 'yes', 'true', '1')) AND (lower(COALESCE(CAST(e.employment_status AS VARCHAR), '')) IN ('active', 'employed', 'currently employed')));

-- View: governed.v_dashboard_department_mix
CREATE VIEW governed.v_dashboard_department_mix AS SELECT e.department_id, COALESCE(CAST(d.department_name AS VARCHAR), CAST(e.department_id AS VARCHAR)) AS department_name, count(DISTINCT e.employee_id) AS employee_count FROM governed.v_dashboard_current_employee AS e LEFT JOIN raw.dim_department AS d ON ((CAST(e.department_id AS VARCHAR) = CAST(d.department_id AS VARCHAR))) GROUP BY 1, 2;

-- View: governed.v_dashboard_exits
CREATE VIEW governed.v_dashboard_exits AS SELECT CAST(month_start_date AS DATE) AS month_start_date, CAST(department_id AS VARCHAR) AS department_id, TRY_CAST(metric_value AS DOUBLE) AS metric_value FROM governed.m03_exits WHERE ((month_start_date IS NOT NULL) AND (metric_value IS NOT NULL) AND ((suppressed IS NULL) OR (lower(CAST(suppressed AS VARCHAR)) NOT IN ('true', '1', 'y'))));

-- View: governed.v_dashboard_headcount
CREATE VIEW governed.v_dashboard_headcount AS SELECT CAST(h.month_start_date AS DATE) AS month_start_date, CAST(h.department_id AS VARCHAR) AS department_id, COALESCE(CAST(d.department_name AS VARCHAR), CAST(h.department_id AS VARCHAR)) AS department_name, TRY_CAST(h.metric_value AS DOUBLE) AS headcount FROM governed.m01_headcount AS h LEFT JOIN raw.dim_department AS d ON ((CAST(h.department_id AS VARCHAR) = CAST(d.department_id AS VARCHAR))) WHERE ((h.month_start_date IS NOT NULL) AND (h.metric_value IS NOT NULL) AND ((h.suppressed IS NULL) OR (lower(CAST(h.suppressed AS VARCHAR)) NOT IN ('true', '1', 'y'))));

-- View: governed.v_dashboard_hires
CREATE VIEW governed.v_dashboard_hires AS SELECT CAST(month_start_date AS DATE) AS month_start_date, CAST(department_id AS VARCHAR) AS department_id, TRY_CAST(metric_value AS DOUBLE) AS metric_value FROM governed.m02_hires WHERE ((month_start_date IS NOT NULL) AND (metric_value IS NOT NULL) AND ((suppressed IS NULL) OR (lower(CAST(suppressed AS VARCHAR)) NOT IN ('true', '1', 'y'))));

-- View: governed.v_dashboard_location_tier
CREATE VIEW governed.v_dashboard_location_tier AS SELECT COALESCE(CAST(l.city_tier AS VARCHAR), 'Unknown') AS location_tier, count(DISTINCT e.employee_id) AS employee_count FROM governed.v_dashboard_current_employee AS e LEFT JOIN raw.dim_location AS l ON ((lower(main."trim"(e.work_location)) = lower(main."trim"(CAST(l.work_location AS VARCHAR))))) GROUP BY 1;

-- View: governed.v_dashboard_work_mode
CREATE VIEW governed.v_dashboard_work_mode AS SELECT COALESCE("nullif"(main."trim"(work_mode), ''), 'Unknown') AS work_mode, count(DISTINCT employee_id) AS employee_count FROM governed.v_dashboard_current_employee GROUP BY 1;

