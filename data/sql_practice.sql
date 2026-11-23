-- Practice database for the SQL lessons (03a-03f) and pandas interview lessons.
-- Rebuilt in memory on every query, so nothing you run can damage it.

CREATE TABLE users (
  user_id     INTEGER PRIMARY KEY,
  name        TEXT,
  country     TEXT,
  channel     TEXT,
  signup_date TEXT
);
INSERT INTO users VALUES
  (1,  'Ann',  'US', 'organic',  '2026-01-01'),
  (2,  'Bob',  'US', 'ads',      '2026-01-01'),
  (3,  'Chen', 'CN', 'organic',  '2026-01-02'),
  (4,  'Dana', 'US', 'referral', '2026-01-03'),
  (5,  'Eli',  'CA', 'ads',      '2026-01-03'),
  (6,  'Fay',  'CN', 'ads',      '2026-01-05'),
  (7,  'Gus',  NULL, 'organic',  '2026-01-06'),
  (8,  'Hana', 'US', 'referral', '2026-01-08'),
  (9,  'Ivan', 'CA', 'organic',  '2026-01-09'),
  (10, 'Jia',  'CN', 'ads',      '2026-01-10');

CREATE TABLE orders (
  order_id   INTEGER PRIMARY KEY,
  user_id    INTEGER,
  order_date TEXT,
  amount     REAL,
  status     TEXT
);
INSERT INTO orders VALUES
  (1001, 1,  '2026-01-02', 30,  'completed'),
  (1002, 1,  '2026-01-05', 50,  'completed'),
  (1003, 1,  '2026-01-20', 20,  'refunded'),
  (1004, 2,  '2026-01-03', 15,  'completed'),
  (1005, 2,  '2026-01-04', 15,  'completed'),
  (1006, 3,  '2026-01-02', 80,  'completed'),
  (1007, 3,  '2026-01-15', 40,  'completed'),
  (1008, 3,  '2026-02-01', 60,  'completed'),
  (1009, 4,  '2026-01-10', 25,  'completed'),
  (1010, 5,  '2026-01-04', 100, 'completed'),
  (1011, 5,  '2026-01-25', 35,  'refunded'),
  (1012, 6,  '2026-01-06', 45,  'completed'),
  (1013, 6,  '2026-02-03', 55,  'completed'),
  (1014, 8,  '2026-01-09', 70,  'completed'),
  (1015, 8,  '2026-02-05', 70,  'completed'),
  (1016, 10, '2026-01-12', 10,  'completed');

CREATE TABLE events (
  user_id    INTEGER,
  event_date TEXT,
  event_type TEXT
);
INSERT INTO events VALUES
  (1, '2026-01-01', 'login'), (1, '2026-01-02', 'login'), (1, '2026-01-02', 'login'),
  (1, '2026-01-03', 'login'), (1, '2026-01-05', 'login'), (1, '2026-01-08', 'login'),
  (2, '2026-01-01', 'login'), (2, '2026-01-02', 'login'),
  (3, '2026-01-02', 'login'), (3, '2026-01-03', 'login'), (3, '2026-01-04', 'login'),
  (3, '2026-01-05', 'login'), (3, '2026-01-09', 'login'),
  (4, '2026-01-03', 'login'),
  (5, '2026-01-03', 'login'), (5, '2026-01-04', 'login'), (5, '2026-01-10', 'login'),
  (6, '2026-01-05', 'login'), (6, '2026-01-06', 'login'), (6, '2026-01-07', 'login'),
  (7, '2026-01-06', 'login'),
  (8, '2026-01-08', 'login'), (8, '2026-01-09', 'login'), (8, '2026-01-15', 'login'),
  (9, '2026-01-09', 'login'), (9, '2026-01-10', 'login'),
  (10, '2026-01-10', 'login'),
  (1, '2026-01-02', 'view'), (1, '2026-01-02', 'cart'), (1, '2026-01-02', 'purchase'),
  (2, '2026-01-02', 'view'), (2, '2026-01-02', 'cart'),
  (3, '2026-01-02', 'view'), (3, '2026-01-02', 'cart'), (3, '2026-01-02', 'purchase'),
  (4, '2026-01-03', 'view'),
  (5, '2026-01-04', 'view'), (5, '2026-01-04', 'cart'), (5, '2026-01-04', 'purchase'),
  (6, '2026-01-06', 'view'), (6, '2026-01-06', 'cart'), (6, '2026-01-06', 'purchase'),
  (7, '2026-01-06', 'view'),
  (8, '2026-01-09', 'view'), (8, '2026-01-09', 'cart'), (8, '2026-01-09', 'purchase'),
  (9, '2026-01-09', 'view'), (9, '2026-01-10', 'cart'),
  (10, '2026-01-10', 'view');

CREATE TABLE employees (
  emp_id     INTEGER PRIMARY KEY,
  name       TEXT,
  dept       TEXT,
  salary     INTEGER,
  manager_id INTEGER
);
INSERT INTO employees VALUES
  (1, 'Alice', 'Eng',   150, NULL),
  (2, 'Brian', 'Eng',   120, 1),
  (3, 'Cathy', 'Eng',   120, 1),
  (4, 'David', 'Eng',   95,  2),
  (5, 'Emma',  'Sales', 90,  1),
  (6, 'Frank', 'Sales', 70,  5),
  (7, 'Grace', 'Sales', 70,  5),
  (8, 'Henry', 'Mkt',   85,  1),
  (9, 'Irene', 'Mkt',   60,  8);
