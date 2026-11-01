-- Counts of distinct students, not assessment attempts.
SELECT COUNT(DISTINCT roll_number) AS students_cleared_java
FROM ps_cleared_course_view
WHERE status ILIKE 'Cleared'
  AND (vertical_name ILIKE '%java%' OR course_name ILIKE '%java%');

-- Top 10 students by number of distinct cleared Java-related course names.
SELECT roll_number, name, COUNT(DISTINCT course_name) AS cleared_java_courses
FROM ps_cleared_course_view
WHERE status ILIKE 'Cleared'
  AND (vertical_name ILIKE '%java%' OR course_name ILIKE '%java%')
GROUP BY roll_number, name
ORDER BY cleared_java_courses DESC, name
LIMIT 10;

-- Cleared vs not-cleared attempts for courses matching backend-related terms.
SELECT status, COUNT(*) AS attempts
FROM ps_cleared_course_view
WHERE course_name ILIKE '%backend%' OR vertical_name ILIKE '%backend%'
GROUP BY status;
