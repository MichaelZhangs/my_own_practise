from utils.mysql import get_db_connection

class User:
    @staticmethod
    def create_user(phone: str, email: str, sex: str, password: str, description: str = None, photo: str = None):
        try:
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    sql = """
                        INSERT INTO user (phone, email, sex, password, description, photo)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(sql, (phone, email, sex, password, description, photo))
                    connection.commit()
                    return cursor.lastrowid  # 返回插入的用户 ID
        except Exception as e:
            print(f"创建用户失败: {str(e)}")
            raise

    @staticmethod
    def get_user_by_phone(phone: str):
        try:
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    sql = "SELECT * FROM user WHERE phone = %s"
                    cursor.execute(sql, (phone,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"查询用户失败: {str(e)}")
            raise

    @staticmethod
    def get_user_by_email(email: str):
        try:
            with get_db_connection() as connection:
                with connection.cursor() as cursor:
                    sql = "SELECT * FROM user WHERE email = %s"
                    cursor.execute(sql, (email,))
                    return cursor.fetchone()
        except Exception as e:
            print(f"查询用户失败: {str(e)}")
            raise