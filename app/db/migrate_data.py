import json
import logging
from datetime import date, datetime, time
import psycopg2
from pymongo import MongoClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_data")


def serialize_datetime(obj):
    if isinstance(obj, (date, time, datetime)):
        return obj.isoformat()
    return obj


def main():
    # PostgreSQL settings
    pg_params = {
        "host": "192.168.1.26",
        "port": 5432,
        "user": "postgres",
        "password": "user@123",
        "database": "astroDB"
    }
    
    # MongoDB settings
    mongo_uri = "mongodb://localhost:27017/"
    mongo_db_name = "astroDB"

    logger.info("Connecting to PostgreSQL...")
    try:
        conn = psycopg2.connect(**pg_params)
        cursor = conn.cursor()
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return

    logger.info("Connecting to MongoDB...")
    try:
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client[mongo_db_name]
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        conn.close()
        return

    logger.info("Fetching users from PostgreSQL...")
    try:
        cursor.execute("SELECT id, email, hashed_password, is_active, created_at, updated_at FROM users;")
        postgres_users = cursor.fetchall()
    except Exception as e:
        logger.error(f"Failed to query users table: {e}")
        conn.close()
        mongo_client.close()
        return

    logger.info(f"Found {len(postgres_users)} users in PostgreSQL. Commencing migration...")

    migrated_users = 0
    migrated_profiles = 0
    migrated_birth_data = 0

    for u_row in postgres_users:
        u_id, u_email, u_hashed_pw, u_is_active, u_created_at, u_updated_at = u_row
        
        # Save to 'users' collection
        mongo_user = {
            "_id": str(u_id),
            "id": str(u_id),
            "email": u_email,
            "hashed_password": u_hashed_pw,
            "is_active": u_is_active,
            "created_at": serialize_datetime(u_created_at),
            "updated_at": serialize_datetime(u_updated_at),
        }
        db.users.replace_one({"_id": str(u_id)}, mongo_user, upsert=True)
        migrated_users += 1

        # Fetch profile
        cursor.execute(
            "SELECT id, first_name, last_name, current_location, created_at, updated_at FROM user_profiles WHERE user_id = %s;",
            (u_id,)
        )
        p_row = cursor.fetchone()
        
        if p_row:
            p_id, p_first, p_last, p_curr_loc, p_created_at, p_updated_at = p_row
            
            # Save to 'user_profiles' collection
            profile_data = {
                "_id": str(p_id),
                "id": str(p_id),
                "user_id": str(u_id),
                "first_name": p_first,
                "last_name": p_last,
                "current_location": p_curr_loc,
                "created_at": serialize_datetime(p_created_at),
                "updated_at": serialize_datetime(p_updated_at),
            }
            db.user_profiles.replace_one({"_id": str(p_id)}, profile_data, upsert=True)
            migrated_profiles += 1

            # Fetch birth data
            cursor.execute(
                "SELECT id, date_of_birth, birth_time, birth_place, latitude, longitude, timezone, dst_handling, timezone_source, coordinate_source, normalized_birth_datetime, calculation_metadata, created_at, updated_at FROM birth_data WHERE profile_id = %s;",
                (p_id,)
            )
            bd_row = cursor.fetchone()
            
            if bd_row:
                bd_id, bd_dob, bd_bt, bd_place, bd_lat, bd_lon, bd_tz, bd_dst, bd_tz_src, bd_coord_src, bd_norm_dt, bd_calc_meta, bd_created_at, bd_updated_at = bd_row
                
                if isinstance(bd_calc_meta, str):
                    try:
                        bd_calc_meta = json.loads(bd_calc_meta)
                    except Exception:
                        pass
                
                # Save to 'birth_data' collection
                birth_data = {
                    "_id": str(bd_id),
                    "id": str(bd_id),
                    "profile_id": str(p_id),
                    "date_of_birth": serialize_datetime(bd_dob),
                    "birth_time": serialize_datetime(bd_bt),
                    "birth_place": bd_place,
                    "latitude": float(bd_lat) if bd_lat is not None else 0.0,
                    "longitude": float(bd_lon) if bd_lon is not None else 0.0,
                    "timezone": bd_tz,
                    "dst_handling": bd_dst,
                    "timezone_source": bd_tz_src,
                    "coordinate_source": bd_coord_src,
                    "normalized_birth_datetime": serialize_datetime(bd_norm_dt),
                    "calculation_metadata": bd_calc_meta or {},
                    "created_at": serialize_datetime(bd_created_at),
                    "updated_at": serialize_datetime(bd_updated_at),
                }
                db.birth_data.replace_one({"_id": str(bd_id)}, birth_data, upsert=True)
                migrated_birth_data += 1

    logger.info(f"Successfully migrated {migrated_users} users, {migrated_profiles} profiles, and {migrated_birth_data} birth data entries to MongoDB!")
    
    conn.close()
    mongo_client.close()


if __name__ == "__main__":
    main()
