import traceback
from typing import Generator
from flask import Flask

from flaskr.service.common.models import AppException, raise_error
from flaskr.service.user.models import User
from flaskr.i18n import _
from ...api.langfuse import langfuse_client as langfuse
from ...service.lesson.const import (
    LESSON_TYPE_TRIAL,
)
from ...service.lesson.models import AICourse, AILesson
from ...service.order.consts import (
    ATTEND_STATUS_BRANCH,
    ATTEND_STATUS_COMPLETED,
    ATTEND_STATUS_IN_PROGRESS,
    ATTEND_STATUS_NOT_STARTED,
    ATTEND_STATUS_RESET,
    ATTEND_STATUS_LOCKED,
    get_attend_status_values,
)
from ...service.order.funs import (
    AICourseLessonAttendDTO,
    init_trial_lesson,
    init_trial_lesson_inner,
)
from ...service.order.models import AICourseLessonAttend
from ...service.study.const import (
    INPUT_TYPE_ASK,
    INPUT_TYPE_START,
    INPUT_TYPE_CONTINUE,
)
from ...service.study.dtos import ScriptDTO
from ...dao import db, redis_client
from .utils import (
    make_script_dto,
    get_script,
    update_lesson_status,
    get_current_lesson,
)
from .input_funcs import BreakException
from .output_funcs import handle_output
from .plugin import handle_input, handle_ui, check_continue
from .utils import make_script_dto_to_stream
from flaskr.service.study.dtos import AILessonAttendDTO


def run_script_inner(
    app: Flask,
    user_id: str,
    course_id: str,
    lesson_id: str = None,
    input: str = None,
    input_type: str = None,
    script_id: str = None,
    log_id: str = None,
) -> Generator[str, None, None]:
    with app.app_context():
        script_info = None
        try:
            attend_status_values = get_attend_status_values()
            user_info = User.query.filter(User.user_id == user_id).first()
            if not lesson_id:
                app.logger.info("lesson_id is None")
                if course_id:
                    course_info = AICourse.query.filter(
                        AICourse.course_id == course_id,
                        AICourse.status == 1,
                    ).first()
                else:
                    course_info = AICourse.query.filter(
                        AICourse.status == 1,
                    ).first()
                    if course_info is None:
                        raise_error("LESSON.HAS_NOT_LESSON")
                if not course_info:
                    raise_error("LESSON.COURSE_NOT_FOUND")
                yield make_script_dto(
                    "teacher_avator", course_info.course_teacher_avator, ""
                )
                course_id = course_info.course_id
                lessons = init_trial_lesson(app, user_id, course_id)
                attend = get_current_lesson(app, lessons)
                lesson_id = attend.lesson_id
                lesson_info = AILesson.query.filter(
                    AILesson.lesson_id == lesson_id,
                ).first()
                if not lesson_info:
                    raise_error("LESSON.LESSON_NOT_FOUND_IN_COURSE")
            else:
                lesson_info = AILesson.query.filter(
                    AILesson.lesson_id == lesson_id,
                ).first()
                if not lesson_info:
                    raise_error("LESSON.LESSON_NOT_FOUND_IN_COURSE")
                course_id = lesson_info.course_id
                app.logger.info(
                    "user_id:{},course_id:{},lesson_id:{},lesson_no:{}".format(
                        user_id, course_id, lesson_id, lesson_info.lesson_no
                    )
                )
                if not lesson_info:
                    raise_error("LESSON.LESSON_NOT_FOUND_IN_COURSE")
                course_info = AICourse.query.filter(
                    AICourse.course_id == course_id,
                    AICourse.status == 1,
                ).first()
                if not course_info:
                    raise_error("LESSON.COURSE_NOT_FOUND")
                # return the teacher avator
                yield make_script_dto(
                    "teacher_avator", course_info.course_teacher_avator, ""
                )

                attend_info = AICourseLessonAttend.query.filter(
                    AICourseLessonAttend.user_id == user_id,
                    AICourseLessonAttend.course_id == course_id,
                    AICourseLessonAttend.lesson_id == lesson_id,
                    AICourseLessonAttend.status != ATTEND_STATUS_RESET,
                ).first()
                if not attend_info:
                    if lesson_info.lesson_type == LESSON_TYPE_TRIAL:
                        app.logger.info(
                            "init trial lesson for user:{} course:{}".format(
                                user_id, course_id
                            )
                        )
                        new_attend_infos = init_trial_lesson_inner(
                            app, user_id, course_id
                        )
                        new_attend_maps = {i.lesson_id: i for i in new_attend_infos}
                        attend_info = new_attend_maps.get(lesson_id, None)
                        if not attend_info:
                            raise_error("LESSON.LESSON_NOT_FOUND_IN_COURSE")
                    else:
                        raise_error("COURSE.COURSE_NOT_PURCHASED")

                if (
                    attend_info.status == ATTEND_STATUS_COMPLETED
                    or attend_info.status == ATTEND_STATUS_LOCKED
                ):

                    parent_no = lesson_info.lesson_no
                    if len(parent_no) >= 2:
                        parent_no = parent_no[:-2]
                    lessons = AILesson.query.filter(
                        AILesson.lesson_no.like(parent_no + "__"),
                        AILesson.course_id == course_id,
                        AILesson.status == 1,
                    ).all()
                    app.logger.info(
                        "study lesson no :{}".format(
                            ",".join([lesson.lesson_no for lesson in lessons])
                        )
                    )
                    lesson_ids = [lesson.lesson_id for lesson in lessons]
                    attend_infos = AICourseLessonAttend.query.filter(
                        AICourseLessonAttend.user_id == user_id,
                        AICourseLessonAttend.course_id == course_id,
                        AICourseLessonAttend.lesson_id.in_(lesson_ids),
                        AICourseLessonAttend.status.in_(
                            [
                                ATTEND_STATUS_NOT_STARTED,
                                ATTEND_STATUS_IN_PROGRESS,
                                ATTEND_STATUS_BRANCH,
                            ]
                        ),
                    ).all()
                    attend_maps = {i.lesson_id: i for i in attend_infos}
                    lessons = sorted(lessons, key=lambda x: x.lesson_no)
                    for lesson in lessons:
                        lesson_attend_info = attend_maps.get(lesson.lesson_id, None)
                        if (
                            len(lesson.lesson_no) > 2
                            and lesson_attend_info
                            and lesson_attend_info.status
                            in [
                                ATTEND_STATUS_NOT_STARTED,
                                ATTEND_STATUS_IN_PROGRESS,
                                ATTEND_STATUS_BRANCH,
                            ]
                        ):
                            lesson_id = lesson_attend_info.lesson_id
                            attend_info = lesson_attend_info
                            break
                attend = AICourseLessonAttendDTO(
                    attend_info.attend_id,
                    attend_info.lesson_id,
                    attend_info.course_id,
                    attend_info.user_id,
                    attend_info.status,
                    attend_info.script_index,
                )
                db.session.flush()
            # Langfuse
            trace_args = {}
            trace_args["user_id"] = user_id
            trace_args["session_id"] = attend.attend_id
            trace_args["input"] = input
            trace_args["name"] = course_info.course_name
            trace = langfuse.trace(**trace_args)
            trace_args["output"] = ""
            next = 0
            is_first_add = False
            # get the script info and the attend updates
            script_info, attend_updates, is_first_add = get_script(
                app, attend_id=attend.attend_id, next=next
            )
            auto_next_lesson_id = None
            next_chapter_no = None
            if len(attend_updates) > 0:
                app.logger.info(f"attend_updates: {attend_updates}")
                for attend_update in attend_updates:
                    if len(attend_update.lesson_no) > 2:
                        yield make_script_dto(
                            "lesson_update", attend_update.__json__(), ""
                        )
                        if next_chapter_no and attend_update.lesson_no.startswith(
                            next_chapter_no
                        ):
                            auto_next_lesson_id = attend_update.lesson_id
                    else:
                        yield make_script_dto(
                            "chapter_update", attend_update.__json__(), ""
                        )
                        if (
                            attend_update.status
                            == attend_status_values[ATTEND_STATUS_NOT_STARTED]
                        ):
                            yield make_script_dto(
                                "next_chapter", attend_update.__json__(), ""
                            )
                            next_chapter_no = attend_update.lesson_no

            if script_info:
                try:
                    # handle user input
                    response = handle_input(
                        app,
                        user_info,
                        input_type,
                        lesson_info,
                        attend,
                        script_info,
                        input,
                        trace,
                        trace_args,
                    )
                    if response:
                        yield from response
                    # check if the script is start or continue
                    if input_type == INPUT_TYPE_START:
                        next = 0
                    else:
                        next = 1
                    while True and input_type != INPUT_TYPE_ASK:
                        if is_first_add:
                            is_first_add = False
                            next = 0
                        script_info, attend_updates, _ = get_script(
                            app, attend_id=attend.attend_id, next=next
                        )
                        next = 1
                        if len(attend_updates) > 0:
                            app.logger.info(f"attend_updates: {attend_updates}")
                            for attend_update in attend_updates:
                                if len(attend_update.lesson_no) > 2:
                                    yield make_script_dto(
                                        "lesson_update", attend_update.__json__(), ""
                                    )
                                else:
                                    yield make_script_dto(
                                        "chapter_update", attend_update.__json__(), ""
                                    )
                                    if (
                                        attend_update.status
                                        == attend_status_values[
                                            ATTEND_STATUS_NOT_STARTED
                                        ]
                                    ):
                                        yield make_script_dto(
                                            "next_chapter", attend_update.__json__(), ""
                                        )
                        if script_info:
                            response = handle_output(
                                app,
                                user_id,
                                lesson_info,
                                attend,
                                script_info,
                                input,
                                trace,
                                trace_args,
                            )
                            if response:
                                yield from response

                            if check_continue(
                                app,
                                user_info,
                                attend,
                                script_info,
                                input,
                                trace,
                                trace_args,
                            ):
                                app.logger.info(f"check_continue: {script_info}")
                                next = 1
                                input_type = INPUT_TYPE_CONTINUE
                                continue
                            else:
                                break
                        else:
                            break
                    if script_info:
                        # 返回下一轮交互
                        # 返回  下一轮的交互方式
                        script_dtos = handle_ui(
                            app,
                            user_info,
                            attend,
                            script_info,
                            input,
                            trace,
                            trace_args,
                        )
                        for script_dto in script_dtos:
                            yield make_script_dto_to_stream(script_dto)
                    else:
                        res = update_lesson_status(app, attend.attend_id)
                        if res:
                            for attend_update in res:
                                if isinstance(attend_update, AILessonAttendDTO):
                                    if len(attend_update.lesson_no) > 2:
                                        yield make_script_dto(
                                            "lesson_update",
                                            attend_update.__json__(),
                                            "",
                                        )
                                        if (
                                            next_chapter_no
                                            and attend_update.lesson_no.startswith(
                                                next_chapter_no
                                            )
                                        ):
                                            auto_next_lesson_id = (
                                                attend_update.lesson_id
                                            )
                                    else:
                                        yield make_script_dto(
                                            "chapter_update",
                                            attend_update.__json__(),
                                            "",
                                        )
                                        if (
                                            attend_update.status
                                            == attend_status_values[
                                                ATTEND_STATUS_NOT_STARTED
                                            ]
                                        ):
                                            yield make_script_dto(
                                                "next_chapter",
                                                attend_update.__json__(),
                                                "",
                                            )
                                            next_chapter_no = attend_update.lesson_no
                                elif isinstance(attend_update, ScriptDTO):
                                    app.logger.info(
                                        f"extend_update_lesson_status: {attend_update}"
                                    )
                                    yield make_script_dto_to_stream(attend_update)
                except BreakException:
                    if script_info:
                        yield make_script_dto("text_end", "", None)
                        script_dtos = handle_ui(
                            app,
                            user_id,
                            attend,
                            script_info,
                            input,
                            trace,
                            trace_args,
                        )
                        for script_dto in script_dtos:
                            yield make_script_dto_to_stream(script_dto)
                    db.session.commit()
                    return
            else:
                app.logger.info("script_info is None,to update attend")
                res = update_lesson_status(app, attend.attend_id)
                if res and len(res) > 0:
                    for attend_update in res:
                        if isinstance(attend_update, AILessonAttendDTO):
                            if len(attend_update.lesson_no) > 2:
                                yield make_script_dto(
                                    "lesson_update", attend_update.__json__(), ""
                                )
                                if (
                                    next_chapter_no
                                    and attend_update.lesson_no.startswith(
                                        next_chapter_no
                                    )
                                ):
                                    auto_next_lesson_id = attend_update.lesson_id
                            else:
                                yield make_script_dto(
                                    "chapter_update", attend_update.__json__(), ""
                                )
                                if (
                                    attend_update.status
                                    == attend_status_values[ATTEND_STATUS_NOT_STARTED]
                                ):
                                    yield make_script_dto(
                                        "next_chapter", attend_update.__json__(), ""
                                    )
                                    next_chapter_no = attend_update.lesson_no
                        elif isinstance(attend_update, ScriptDTO):
                            app.logger.info(
                                f"extend_update_lesson_status: {attend_update}"
                            )
                            yield make_script_dto_to_stream(attend_update)
            db.session.commit()
            if auto_next_lesson_id:
                app.logger.info("auto_next_lesson_id:{}".format(auto_next_lesson_id))
                yield from run_script_inner(
                    app,
                    user_id,
                    course_id,
                    auto_next_lesson_id,
                    input_type=INPUT_TYPE_START,
                )
        except GeneratorExit:
            db.session.rollback()
            app.logger.info("GeneratorExit")


def run_script(
    app: Flask,
    user_id: str,
    course_id: str,
    lesson_id: str = None,
    input: str = None,
    input_type: str = None,
    script_id: str = None,
    log_id: str = None,
) -> Generator[ScriptDTO, None, None]:
    timeout = 5 * 60
    blocking_timeout = 1
    lock_key = app.config.get("REDIS_KEY_PRRFIX") + ":run_script:" + user_id
    lock = redis_client.lock(
        lock_key, timeout=timeout, blocking_timeout=blocking_timeout
    )
    if lock.acquire(blocking=True):
        try:
            app.logger.info("run_script with lock")
            yield from run_script_inner(
                app, user_id, course_id, lesson_id, input, input_type, script_id, log_id
            )
            app.logger.info("run_script end")
        except Exception as e:
            app.logger.error("run_script error")
            # 输出详细的错误信息
            app.logger.error(e)
            # 输出异常信息
            error_info = {
                "name": type(e).__name__,
                "description": str(e),
                "traceback": traceback.format_exc(),
            }

            if isinstance(e, AppException):
                app.logger.info(error_info)
                yield make_script_dto("text", str(e), None)
            else:
                app.logger.error(error_info)
                yield make_script_dto("text", _("COMMON.UNKNOWN_ERROR"), None)
            yield make_script_dto("text_end", "", None)
        finally:

            lock.release()
            app.logger.info("run_script release lock")
        return
    else:

        app.logger.info("lockfail")
        yield make_script_dto("text_end", "", None)
    return
