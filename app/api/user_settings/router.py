class USERSETTING_ROUTES:

    # @staticmethod
    def get_routes(blueprint):
        if blueprint == 'validation':
            path = '/validate_account'
            return path
        elif blueprint == "delete_broker_account":

            path = '/delete_credentials'
            return path
        elif blueprint == "update_password":
            path = '/update_password'
            return path
        elif blueprint == "logout":
            path = '/logout/{username:str}/{broker_user_id:str}'
            return path
        elif blueprint == "forgot_password":
            path = '/forgot_password/{username:str}'
            return path
        elif blueprint == "verify_otp":
            path = '/verify_otp/{username:str}'
            return path
