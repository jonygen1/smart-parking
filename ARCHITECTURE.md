# החלטות ארכיטקטוניות

לכל החלטה: מה בחרנו, למה, ומה החלופה.

## 1. Python + Flask ל-API
- **למה:** קוד קצר וקריא, קל להסביר ב-Code Review. ספריית `redis-py` הרשמית.
- **בפרודקשן:** `gunicorn` עם 2 workers ולא השרת המובנה של Flask (שמיועד לפיתוח בלבד).
- **חלופה:** Node.js + Express. היה עובד באותה מידה.

## 2. Nginx כ-Reverse Proxy ל-API
- הדפדפן קורא ל-`/api/...` **באותו origin** של הדף, ו-Nginx מעביר את הבקשה ל-`http://api:5000` ברשת הפנימית של Docker.
- **למה:** אין בעיית CORS, וכתובת ה-API לא כתובה בקוד ה-JS (אפשר להעביר את המערכת לשרת אחר בלי לשנות קוד).
- `api` הוא שם השירות ב-compose. Docker מריץ DNS פנימי שמתרגם שם שירות ל-IP של ה-container.

## 3. Redis: מבנה הנתונים
| Key | סוג | למה הסוג הזה |
|-----|-----|--------------|
| `parking:inside` | Sorted Set (score = זמן כניסה) | `ZCARD` נותן כמה רכבים יש ב-O(1), `ZREVRANGE` מחזיר אותם ממוינים מהחדש לישן, ו-`ZSCORE` בודק אם רכב כבר בפנים |
| `car:<plate>` | Hash | כל פרטי הרכב (זמן, שער, הודעה) תחת מפתח אחד |
| `parking:history` | List | `LPUSH` + `LTRIM 0 19` = רק 20 היציאות האחרונות, בלי שהרשימה תגדל לנצח |
| `stats:total_entries`, `stats:revenue` | String (מונה) | `INCR` / `INCRBY` אטומיים |

## 4. מניעת Race Condition בכניסה
בדיקת "יש מקום?" ואחריה "הוסף רכב" הן שתי פעולות. אם שתי מצלמות שולחות באותו רגע, שתיהן יכולות לראות "יש מקום אחד" ולהכניס שני רכבים.
**הפתרון:** `WATCH parking:inside` + `MULTI/EXEC` (`r.transaction(...)` ב-redis-py). אם המפתח השתנה בין הבדיקה לכתיבה, Redis מבטל את הטרנזקציה והקוד מנסה שוב.

## 5. Persistence
- `--appendonly yes`: כל כתיבה נרשמת לקובץ AOF. `--appendfsync everysec`: הקובץ נכתב לדיסק פעם בשנייה, כלומר במקרה הגרוע מאבדים שנייה אחת של נתונים.
- `--save 60 1`: גם Snapshot (קובץ RDB) כל 60 שניות אם השתנה משהו.
- `/data` הוא **Named Volume** (`redis-data`) ולא bind mount: Docker מנהל אותו, הוא עובד זהה ב-Windows, Mac ו-Linux, ואין בעיות הרשאות.

## 6. Healthchecks ו-`depends_on: condition: service_healthy`
`depends_on` רגיל מחכה רק שה-container **יעלה**, לא שהשירות **מוכן**. לכן:
- `api` מחכה ש-Redis יענה ל-`PING`.
- `web` ו-`camera` מחכים ש-`/api/health` יחזיר 200.
- Nginx חייב שהשם `api` יהיה קיים כשהוא עולה, אחרת הוא נופל עם `host not found in upstream`.
- `python:slim` לא כולל `curl`, לכן ה-healthcheck של ה-API כתוב ב-Python.

## 7. אבטחה בסיסית
- Redis **לא** חשוף החוצה (אין `ports:`), נגיש רק מתוך הרשת של ה-compose.
- ה-containers של Python רצים כמשתמש רגיל (`USER appuser`) ולא כ-root.
- ב-JS בונים את ה-DOM עם `textContent` ולא `innerHTML`, כך שלוחית או הודעה עם קוד HTML לא תורץ בדפדפן (XSS).

## 8. Dockerfile: סדר השכבות
`COPY requirements.txt` ו-`pip install` **לפני** `COPY app.py`. כל עוד `requirements.txt` לא השתנה, Docker משתמש בשכבה מה-cache ולא מתקין מחדש את הספריות בכל שינוי קוד, כך שה-build מהיר יותר.

## 9. Polling ולא WebSocket
לוח הבקרה שואל את ה-API כל 2 שניות. זה פשוט, עובד דרך כל proxy, ומתאים לדרישת המטלה. בחניון אמיתי עם הרבה שומרים WebSocket או Server-Sent Events היו חוסכים בקשות.

## 10. סימולטור מצלמה כ-container נפרד
כך ה-POST מגיע מ"מכשיר" אחר ברשת, כמו במציאות, והדמו חי בלי שמישהו ילחץ. הוא כתוב רק עם ספריות סטנדרטיות של Python, כך שה-Image שלו לא צריך `pip install`.

## 11. הפרדה בין `logic.py` ל-`app.py`
הלוגיקה (נרמול לוחית, חישוב מחיר) לא תלויה ב-Flask או ב-Redis, ולכן אפשר לבדוק אותה ב-`pytest` ב-CI בלי להרים שרתים.
