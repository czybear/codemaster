from flask import Flask, request
from flaskr.service.order.funs import fix_attend_info
from flaskr.route.common import bypass_token_validation, make_common_response


def register_tools_handler(app: Flask, path_prefix: str) -> Flask:
    # app.logger.info('register_study_handler is called, path_prefix is {}'.format(path_prefix))
    @bypass_token_validation
    @app.route(path_prefix + "/fix", methods=["GET"])
    def reset_course():
        """
        重置用户学习信息
        ---
        tags:
          - 工具

        """
        user_id = request.args.get("user_id")
        course_id = request.args.get("course_id")
        return make_common_response(fix_attend_info(app, user_id, course_id))

    return app
