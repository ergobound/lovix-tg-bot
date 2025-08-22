import mysql.connector
import os

class Mysql:
    '''Подключение к базе данных'''
    
    def __init__(self, user, password, host, database):
        self.connection = mysql.connector.connect(user=user,
                                            password=password,
                                            host=host,
                                            database=database)

    def __call__(self, query, data=None):
        try:
            result = None
            # if not connection.is_connected():
            #     connection = mysql.connector.connect(user=user, password=password,
            #                                             host=host, database=database)
            self.connection.reconnect()

            cursor = self.connection.cursor()
            try:
                cursor.execute(query, data)
            except mysql.connector.errors.IntegrityError as err:
                print('Один из элементов является дубликатом.\n' + err.msg)
                # return mysql.connector.errors.IntegrityError
                return None
            except mysql.connector.errors.DataError as err:
                print(err, err.msg)
                # return 'Слишком большое количество символов.'
                return None
            if cursor.description is None:
                self.connection.commit()
                print(cursor)         
                result = {'lastrowid': cursor.lastrowid, # получить id последнего добавленного
                        'rowcount': cursor.rowcount}  # получить количество удаленных/добавленных строк
            else:
                result = list(cursor)
            try:
                cursor.close()
                self.connection.close()
            except mysql.connector.errors.InternalError:
                # return 'Обнаружен непрочитанный результат.'
                return None
            return result
            
        except BaseException as err:
            # logging.info('Глобальная ошибка: ' + str(err))
            print('Глобальная ошибка: ' + str(err))
            # return 'Произошла ошибка в функции mysql_query. Обратитесь к создателю телеграм бота!'
            return None