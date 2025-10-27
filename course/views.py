from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import json
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import CreateView
from django_filters.views import FilterView
from requests import request
from course.forms import AddStudentToCourseForm
from accounts.decorators import lecturer_required, student_required
from accounts.views import admin_or_lecturer_required
from core.models import Semester
from quiz.models import Quiz
from course.filters import CourseAllocationFilter, ProgramFilter
from course.forms import (
    CourseAddForm,
    CourseAllocationForm,
    EditCourseAllocationForm,
    ProgramForm,
    UploadFormFile,
    UploadFormVideo,
)
from course.models import (
    Course,
    CourseAllocation,
    Program,
    StudentMaterialProgress,
    Upload,
    UploadVideo
)
from collections import defaultdict
from accounts.models import User, Student
from django.utils.crypto import get_random_string
from result.models import TakenCourse
from accounts.utils import send_new_account_email
import re


# ########################################################
# Program Views
# ########################################################


@method_decorator([login_required, admin_or_lecturer_required], name="dispatch")
class ProgramFilterView(FilterView):
    filterset_class = ProgramFilter
    template_name = "course/program_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Programs"
        return context


@login_required
@admin_or_lecturer_required
def program_add(request):
    if request.method == "POST":
        form = ProgramForm(request.POST)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"{program.title} program has been created.")
            return redirect("programs")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = ProgramForm()
    return render(
        request, "course/program_add.html", {"title": "Add Program", "form": form}
    )


@login_required
def program_detail(request, pk):
    program = get_object_or_404(Program, pk=pk)
    courses = Course.objects.filter(program_id=pk).order_by("-year")
    credits = courses.aggregate(total_credits=Sum("credit"))
    paginator = Paginator(courses, 10)
    page = request.GET.get("page")
    courses = paginator.get_page(page)
    return render(
        request,
        "course/program_single.html",
        {
            "title": program.title,
            "program": program,
            "courses": courses,
            "credits": credits,
        },
    )


@login_required
@admin_or_lecturer_required
def program_edit(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        form = ProgramForm(request.POST, instance=program)
        if form.is_valid():
            program = form.save()
            messages.success(request, f"{program.title} program has been updated.")
            return redirect("programs")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = ProgramForm(instance=program)
    return render(
        request, "course/program_add.html", {"title": "Edit Program", "form": form}
    )


@login_required
@admin_or_lecturer_required
def program_delete(request, pk):
    program = get_object_or_404(Program, pk=pk)
    title = program.title
    program.delete()
    messages.success(request, f"Program {title} has been deleted.")
    return redirect("programs")


# ########################################################
# Course Views
# ########################################################

@login_required
def course_list_view(request):
    courses = Course.objects.order_by("-year")
    paginator = Paginator(courses, 10)
    page = request.GET.get("page")
    courses = paginator.get_page(page)
    return render(
        request,
        "course/course_list_view.html",
        {
            "courses": courses,
        },
    )


@login_required
def course_single_old(request, slug):
    course = get_object_or_404(Course, slug=slug)
    files = Upload.objects.filter(course__slug=slug)
    videos = UploadVideo.objects.filter(course__slug=slug)
    lecturers = CourseAllocation.objects.filter(courses__pk=course.id)
    return render(
        request,
        "course/course_single.html",
        {
            "title": course.title,
            "course": course,
            "files": files,
            "videos": videos,
            "lecturers": lecturers,
            "media_url": settings.MEDIA_URL,
        },
    )

# @login_required
# def course_single(request, slug):
#     course = get_object_or_404(Course, slug=slug)
#     print('inside course_single')
#     print()
#     if request.user.is_student:
#         # For students: show only available content, ordered by module and title
#         files = Upload.objects.filter(
#             course__slug=slug,
#             is_available=True
#         ).order_by('module_number', 'title')
#
#         videos = UploadVideo.objects.filter(
#             course__slug=slug,
#             is_available=True
#         ).order_by('module_number', 'title')
#     else:
#         # For non-students (lecturers, admins): show all content as before
#         files = Upload.objects.filter(course__slug=slug)
#         videos = UploadVideo.objects.filter(course__slug=slug)
#
#     # Get student progress if user is a student
#     completed_materials = set()
#     current_taken_course = None
#     if request.user.is_student:
#         try:
#             print('inside if block')
#
#             current_taken_course = TakenCourse.objects.get(
#                 student__pk=request.user.id,
#                 course=course
#             )
#
#             print(current_taken_course)
#
#             progress_records = StudentMaterialProgress.objects.filter(
#                 taken_course=current_taken_course
#             ).values_list('material_id', 'material_type')
#
#             completed_materials = {(material_id, material_type) for material_id, material_type in progress_records}
#         except TakenCourse.DoesNotExist:
#             completed_materials = set()
#
#     # Group materials by module number
#     materials_by_module = defaultdict(list)
#
#     # Add files with content_type indicator
#     for file in files:
#         file.content_type = 'file'
#         file.is_completed = (file.id, 'file') in completed_materials
#         module_key = file.module_number or 0  # Use 0 for None values
#         materials_by_module[module_key].append(file)
#
#     # Add videos with content_type indicator
#     for video in videos:
#         video.content_type = 'video'
#         video.is_completed = (video.id, 'video') in completed_materials
#         module_key = video.module_number or 0  # Use 0 for None values
#         materials_by_module[module_key].append(video)
#
#     # Sort materials within each module by title
#     for module_materials in materials_by_module.values():
#         module_materials.sort(key=lambda x: x.title or '')
#
#     # Convert to regular dict and sort by module number
#     materials_by_module = dict(sorted(materials_by_module.items()))
#
#     lecturers = CourseAllocation.objects.filter(courses__pk=course.id)
#
#     return render(
#         request,
#         "course/course_single.html",
#         {
#             "title": course.title,
#             "course": course,
#             "materials_by_module": materials_by_module,
#             "lecturers": lecturers,
#             "media_url": settings.MEDIA_URL,
#             "current_taken_course_id": current_taken_course.id if current_taken_course else None,
#         },
#     )

@login_required
def course_single(request, slug):
    course = get_object_or_404(Course, slug=slug)

    print(f"User: {request.user}")
    print(f"User ID: {request.user.id}")
    print(f"Is student: {request.user.is_student}")
    print(f"Course: {course}")

    if request.user.is_student:
        files = Upload.objects.filter(
            course__slug=slug,
            is_available=True
        ).order_by('module_number', 'title')

        videos = UploadVideo.objects.filter(
            course__slug=slug,
            is_available=True
        ).order_by('module_number', 'title')
    else:
        files = Upload.objects.filter(course__slug=slug)
        videos = UploadVideo.objects.filter(course__slug=slug)

    # Get student progress if user is a student
    completed_materials = set()
    current_taken_course = None
    if request.user.is_student:
        try:
            # First, get the Student record using the user_id

            student = Student.objects.get(student_id=request.user.id)
            print(f"Found student record: {student} (ID: {student.id})")

            # Now use the student.id (not user.id) for TakenCourse lookup
            current_taken_course = TakenCourse.objects.filter(
                student_id=student.id,  # Use student.id, not request.user.id
                course_id=course.id
            ).first()

            print(f"Current taken course: {current_taken_course}")

            if current_taken_course:
                progress_records = StudentMaterialProgress.objects.filter(
                    taken_course=current_taken_course
                ).values_list('material_id', 'material_type')

                completed_materials = {(material_id, material_type) for material_id, material_type in progress_records}
            else:
                print("No TakenCourse found for this student and course")

        except Student.DoesNotExist:
            print("Student record not found for this user")
            completed_materials = set()
        except Exception as e:
            print(f"Error getting taken course: {e}")
            completed_materials = set()

    # Rest of your existing code...
    materials_by_module = defaultdict(list)

    for file in files:
        file.content_type = 'file'
        file.is_completed = (file.id, 'file') in completed_materials
        module_key = file.module_number or 0
        materials_by_module[module_key].append(file)

    for video in videos:
        video.content_type = 'video'
        video.is_completed = (video.id, 'video') in completed_materials
        module_key = video.module_number or 0
        materials_by_module[module_key].append(video)

    for module_materials in materials_by_module.values():
        module_materials.sort(key=lambda x: x.title or '')

    materials_by_module = dict(sorted(materials_by_module.items()))

    lecturers = CourseAllocation.objects.filter(courses__pk=course.id)

    print(f"Final current_taken_course_id: {current_taken_course.id if current_taken_course else None}")

    return render(
        request,
        "course/course_single.html",
        {
            "title": course.title,
            "course": course,
            "materials_by_module": materials_by_module,
            "lecturers": lecturers,
            "media_url": settings.MEDIA_URL,
            "current_taken_course_id": current_taken_course.id if current_taken_course else None,
        },
    )

@login_required
@admin_or_lecturer_required
def course_add(request, pk):
    program = get_object_or_404(Program, pk=pk)
    if request.method == "POST":
        form = CourseAddForm(request.POST)
        if form.is_valid():
            course = form.save()
            # If the creator is a lecturer, auto-assign them to the course
            if request.user.is_lecturer:
                allocation, created = CourseAllocation.objects.get_or_create(lecturer=request.user)
                allocation.courses.add(course)

            messages.success(
                request, f"{course.title} ({course.code}) has been created."
            )
            return redirect("program_detail", pk=program.pk)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = CourseAddForm(initial={"program": program})
    return render(
        request,
        "course/course_add.html",
        {"title": "Add Course", "form": form, "program": program},
    )

@login_required
@admin_or_lecturer_required
def course_edit(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == "POST":
        form = CourseAddForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(
                request, f"{course.title} ({course.code}) has been updated."
            )
            return redirect("program_detail", pk=course.program.pk)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = CourseAddForm(instance=course)
    return render(
        request, "course/course_add.html", {"title": "Edit Course", "form": form}
    )

@login_required
@admin_or_lecturer_required
@transaction.atomic
def course_duplicate(request, pk):
    original_course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseAddForm(request.POST)
        if form.is_valid():
            new_course = form.save(commit=False)
            new_course.id = None
            new_course.save()

            # Count original files
            upload_count = Upload.objects.filter(course_id=pk).count()
            video_count = UploadVideo.objects.filter(course_id=pk).count()

            # Duplicate uploads
            for upload in Upload.objects.filter(course_id=pk):
                Upload.objects.create(
                    title=upload.title,
                    file=upload.file,  # Same S3 file reference
                    course_id=new_course.id,  # New course foreign key
                )

            # Duplicate video uploads
            for video in UploadVideo.objects.filter(course_id=pk):
                UploadVideo.objects.create(
                    title=video.title,
                    video=video.video,  # Same S3 video reference
                    course_id=new_course.id,  # New course foreign key
                )

            # Duplicate quizzes and their questions
            total_questions = 0
            quiz_count = Quiz.objects.filter(course_id=pk).count()

            for original_quiz in Quiz.objects.filter(course_id=pk):
                # Create new quiz
                new_quiz = Quiz.objects.create(
                    title=original_quiz.title,
                    description=original_quiz.description,
                    course_id=new_course.id,
                    pass_mark=getattr(original_quiz, 'pass_mark', None),
                    single_attempt=getattr(original_quiz, 'single_attempt', False),
                    random_order=getattr(original_quiz, 'random_order', False),
                    answers_at_end=getattr(original_quiz, 'answers_at_end', False),
                    exam_paper=getattr(original_quiz, 'exam_paper', False),
                    draft=getattr(original_quiz, 'draft', False),
                )

                # Copy the question relationships
                original_questions = original_quiz.question_set.all()
                new_quiz.question_set.set(original_questions)

                total_questions += original_questions.count()

            # Update your success message
            messages.success(
                request,
                f"Course '{new_course.title}' duplicated with {upload_count} files, "
                f"{video_count} videos, {quiz_count} quizzes, and {total_questions} questions!"
            )


            return redirect('/programs/course/duplicate/', slug=new_course.slug)
        messages.error(request, "Correct the error(s) below.")
    else:
        original_course.title = 'Copy of ' + original_course.title
        original_course.code = 'Copy-' + original_course.code
        form = CourseAddForm(instance=original_course)
    return render(
        request, "course/course_duplicate.html", {"title": "Duplicate Course", "form": form}
    )

@login_required
@admin_or_lecturer_required
def course_delete(request, slug):
    course = get_object_or_404(Course, slug=slug)
    title = course.title
    program_id = course.program.id
    course.delete()
    messages.success(request, f"Course {title} has been deleted.")
    return redirect("program_detail", pk=program_id)


# ########################################################
# Course Allocation Views
# ########################################################


@method_decorator([login_required, admin_or_lecturer_required], name="dispatch")
class CourseAllocationFormView(CreateView):
    form_class = CourseAllocationForm
    template_name = "course/course_allocation_form.html"

    def form_valid(self, form):
        lecturer = form.cleaned_data["lecturer"]
        selected_courses = form.cleaned_data["courses"]
        allocation, created = CourseAllocation.objects.get_or_create(lecturer=lecturer)
        allocation.courses.set(selected_courses)
        messages.success(
            self.request, f"Courses allocated to {lecturer.get_full_name} successfully."
        )
        return redirect("course_allocation_view")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Assign Course"
        return context


@method_decorator([login_required, admin_or_lecturer_required], name="dispatch")
class CourseAllocationFilterView(FilterView):
    filterset_class = CourseAllocationFilter
    template_name = "course/course_allocation_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Course Allocations"
        return context


@login_required
@lecturer_required
def edit_allocated_course(request, pk):
    allocation = get_object_or_404(CourseAllocation, pk=pk)
    if request.method == "POST":
        form = EditCourseAllocationForm(request.POST, instance=allocation)
        if form.is_valid():
            form.save()
            messages.success(request, "Course allocation has been updated.")
            return redirect("course_allocation_view")
        messages.error(request, "Correct the error(s) below.")
    else:
        form = EditCourseAllocationForm(instance=allocation)
    return render(
        request,
        "course/course_allocation_form.html",
        {"title": "Edit Course Allocation", "form": form},
    )


@login_required
@lecturer_required
def deallocate_course(request, pk):
    allocation = get_object_or_404(CourseAllocation, pk=pk)
    allocation.delete()
    messages.success(request, "Successfully deallocated courses.")
    return redirect("course_allocation_view")


# ########################################################
# File Upload Views
# ########################################################


@login_required
@lecturer_required
def handle_file_upload(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == "POST":
        form = UploadFormFile(request.POST, request.FILES)
        if form.is_valid():
            upload = form.save(commit=False)
            upload.course = course
            upload.save()
            messages.success(request, f"{upload.title} has been uploaded.")
            return redirect("course_detail", slug=slug)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = UploadFormFile()
    return render(
        request,
        "upload/upload_file_form.html",
        {"title": "File Upload", "form": form, "course": course},
    )


@login_required
@lecturer_required
def handle_file_edit(request, slug, file_id):
    course = get_object_or_404(Course, slug=slug)
    upload = get_object_or_404(Upload, pk=file_id)
    if request.method == "POST":
        form = UploadFormFile(request.POST, request.FILES, instance=upload)
        if form.is_valid():
            upload = form.save()
            messages.success(request, f"{upload.title} has been updated.")
            return redirect("course_detail", slug=slug)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = UploadFormFile(instance=upload)
    return render(
        request,
        "upload/upload_file_form.html",
        {"title": "Edit File", "form": form, "course": course},
    )


@login_required
@lecturer_required
def handle_file_delete(request, slug, file_id):
    upload = get_object_or_404(Upload, pk=file_id)
    title = upload.title
    upload.delete()
    messages.success(request, f"{title} has been deleted.")
    return redirect("course_detail", slug=slug)


# @login_required
# @csrf_exempt
# def toggle_material_progress(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             print(f"Parsed data: {data}")
#
#             material_id = data.get('material_id')
#             material_type = data.get('material_type')
#             is_checked = data.get('is_checked')
#             taken_course_id = data.get('taken_course_id')
#
#             if not taken_course_id:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': 'Missing taken_course_id'
#                 }, status=400)
#
#             taken_course = get_object_or_404(TakenCourse, id=taken_course_id)
#
#             # Verify the taken_course belongs to the current user
#             if taken_course.student.pk != request.user.id:
#                 return JsonResponse({
#                     'status': 'error',
#                     'message': 'Unauthorized'
#                 }, status=403)
#
#             if is_checked:
#                 progress, created = StudentMaterialProgress.objects.get_or_create(
#                     taken_course=taken_course,
#                     material_id=material_id,
#                     material_type=material_type
#                 )
#                 print(f"Progress created: {created}")
#                 return JsonResponse({
#                     'status': 'success',
#                     'action': 'created',
#                     'message': 'Material marked as completed!'
#                 })
#             else:
#                 deleted_count, _ = StudentMaterialProgress.objects.filter(
#                     taken_course=taken_course,
#                     material_id=material_id,
#                     material_type=material_type
#                 ).delete()
#                 print(f"Deleted count: {deleted_count}")
#                 return JsonResponse({
#                     'status': 'success',
#                     'action': 'deleted',
#                     'message': 'Material marked as incomplete!'
#                 })
#
#         except json.JSONDecodeError as e:
#             print(f"JSON decode error: {e}")
#             return JsonResponse({
#                 'status': 'error',
#                 'message': f'Invalid JSON: {str(e)}'
#             }, status=400)
#         except Exception as e:
#             print(f"General error: {e}")
#             return JsonResponse({
#                 'status': 'error',
#                 'message': str(e)
#             }, status=400)
#
#     return JsonResponse({
#         'status': 'error',
#         'message': 'Invalid request method'
#     }, status=405)

# ########################################################
# Video Upload Views
# ########################################################

@login_required
@csrf_exempt
def toggle_material_progress(request):
    print(f"Request method: {request.method}")
    print(f"Request body: {request.body}")

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"Parsed data: {data}")

            material_id = data.get('material_id')
            material_type = data.get('material_type')
            is_checked = data.get('is_checked')
            taken_course_id = data.get('taken_course_id')

            print(
                f"Material ID: {material_id}, Type: {material_type}, Checked: {is_checked}, TakenCourse ID: {taken_course_id}")

            if not taken_course_id or taken_course_id == 'None':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing or invalid taken_course_id'
                }, status=400)

            taken_course = get_object_or_404(TakenCourse, id=taken_course_id)
            print(f"Found taken_course: {taken_course}")

            # Get the student record to verify ownership
            from accounts.models import Student
            student = Student.objects.get(student_id=request.user.id)

            # Verify the taken_course belongs to the current student
            if taken_course.student_id != student.id:  # Compare with student.id
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unauthorized'
                }, status=403)

            if is_checked:
                progress, created = StudentMaterialProgress.objects.get_or_create(
                    taken_course=taken_course,
                    material_id=material_id,
                    material_type=material_type
                )
                print(f"Progress created: {created}")
                return JsonResponse({
                    'status': 'success',
                    'action': 'created',
                    'message': 'Material marked as completed!'
                })
            else:
                deleted_count, _ = StudentMaterialProgress.objects.filter(
                    taken_course=taken_course,
                    material_id=material_id,
                    material_type=material_type
                ).delete()
                print(f"Deleted count: {deleted_count}")
                return JsonResponse({
                    'status': 'success',
                    'action': 'deleted',
                    'message': 'Material marked as incomplete!'
                })

        except Student.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Student record not found'
            }, status=400)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid JSON: {str(e)}'
            }, status=400)
        except Exception as e:
            print(f"General error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@login_required
@lecturer_required
def handle_video_upload(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == "POST":
        form = UploadFormVideo(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.course = course
            video.save()
            messages.success(request, f"{video.title} has been uploaded.")
            return redirect("course_detail", slug=slug)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = UploadFormVideo()
    return render(
        request,
        "upload/upload_video_form.html",
        {"title": "Video Upload", "form": form, "course": course},
    )


@login_required
def handle_video_single(request, slug, video_slug):
    course = get_object_or_404(Course, slug=slug)
    video = get_object_or_404(UploadVideo, slug=video_slug)
    return render(
        request,
        "upload/video_single.html",
        {"video": video, "course": course},
    )


@login_required
@lecturer_required
def handle_video_edit(request, slug, video_slug):
    course = get_object_or_404(Course, slug=slug)
    video = get_object_or_404(UploadVideo, slug=video_slug)
    if request.method == "POST":
        form = UploadFormVideo(request.POST, request.FILES, instance=video)
        if form.is_valid():
            video = form.save()
            messages.success(request, f"{video.title} has been updated.")
            return redirect("course_detail", slug=slug)
        messages.error(request, "Correct the error(s) below.")
    else:
        form = UploadFormVideo(instance=video)
    return render(
        request,
        "upload/upload_video_form.html",
        {"title": "Edit Video", "form": form, "course": course},
    )


@login_required
@lecturer_required
def handle_video_delete(request, slug, video_slug):
    video = get_object_or_404(UploadVideo, slug=video_slug)
    title = video.title
    video.delete()
    messages.success(request, f"{title} has been deleted.")
    return redirect("course_detail", slug=slug)

# ########################################################
# Add Student to Course (Admin and lecturer)
# ########################################################

@login_required
@admin_or_lecturer_required
def add_student_to_course(request, slug):
    course = get_object_or_404(Course, slug=slug)

    # Bulk Add Students
    if request.method == "POST" and "bulk_add" in request.POST:
        emails_input = request.POST.get("emails", "")
        emails = [e.strip() for e in re.split('[,\n\r ]+', emails_input) if e.strip()]
        if len(emails) > 50:
            messages.error(request, "You can only add up to 50 students at a time.")
            return redirect("add_student_to_course", slug=course.slug)

        added, already, created = [], [], []

        for email in emails:
            # Create or get user
            user, user_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "is_student": True,
                    "is_active": True,
                },
            )

            # If new user → set password + send email
            if user_created:
                password = get_random_string(10)
                user.set_password(password)
                user.save()
                send_new_account_email(user, password)
                created.append(email)

            # Ensure student profile exists
            student_profile, _ = Student.objects.get_or_create(student=user)

            # Enroll student in course if not already
            if not TakenCourse.objects.filter(student=student_profile, course=course).exists():
                TakenCourse.objects.create(student=student_profile, course=course)
                added.append(email)
            else:
                already.append(email)

        # Feedback messages
        if added:
            messages.success(request, f"Added to course: {', '.join(added)}")
        if created:
            messages.info(request, f"Accounts created & emailed: {', '.join(created)}")
        if already:
            messages.warning(request, f"Already enrolled: {', '.join(already)}")

        return redirect("add_student_to_course", slug=course.slug)

    # Single Add 
    if request.method == "POST" and "single_add" in request.POST:
        form = AddStudentToCourseForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            first_name = form.cleaned_data.get("first_name", "")
            last_name = form.cleaned_data.get("last_name", "")

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "first_name": first_name,
                    "last_name": last_name,
                    "is_student": True,
                    "is_active": True,
                },
            )

            if created:
                password = get_random_string(10)
                user.set_password(password)
                user.save()
                send_new_account_email(user, password)

            student_profile, _ = Student.objects.get_or_create(student=user)

            if not TakenCourse.objects.filter(student=student_profile, course=course).exists():
                TakenCourse.objects.create(student=student_profile, course=course)
                messages.success(request, f"{email} has been added to {course.title}.")
            else:
                messages.info(request, f"{email} is already enrolled in {course.title}.")

            return redirect("course_detail", slug=slug)

    else:
        form = AddStudentToCourseForm()

    return render(
        request,
        "course/add_student_to_course.html",
        {"title": f"Add Student to {course.title}", "form": form, "course": course},
    )

@login_required
@student_required
def course_registration(request):
    if request.method == "POST":
        student = Student.objects.get(student__pk=request.user.id)
        ids = ()
        data = request.POST.copy()
        data.pop("csrfmiddlewaretoken", None)  # remove csrf_token
        for key in data.keys():
            ids = ids + (str(key),)
        for s in range(0, len(ids)):
            course = Course.objects.get(pk=ids[s])
            obj = TakenCourse.objects.create(student=student, course=course)
            obj.save()
        messages.success(request, "Courses registered successfully!")
        return redirect("course_registration")
    else:
        current_semester = Semester.objects.filter(is_current_semester=True).first()
        if not current_semester:
            messages.error(request, "No active semester found.")
            return render(request, "course/course_registration.html")

        # student = Student.objects.get(student__pk=request.user.id)
        student = get_object_or_404(Student, student__id=request.user.id)
        taken_courses = TakenCourse.objects.filter(student__student__id=request.user.id)
        t = ()
        for i in taken_courses:
            t += (i.course.pk,)

        courses = (
            Course.objects.filter(
                program__pk=student.program.id,
                level=student.level,
                semester=current_semester,
            )
            .exclude(id__in=t)
            .order_by("year")
        )
        all_courses = Course.objects.filter(
            level=student.level, program__pk=student.program.id
        )

        no_course_is_registered = False  # Check if no course is registered
        all_courses_are_registered = False

        registered_courses = Course.objects.filter(level=student.level).filter(id__in=t)
        if (
            registered_courses.count() == 0
        ):  # Check if number of registered courses is 0
            no_course_is_registered = True

        if registered_courses.count() == all_courses.count():
            all_courses_are_registered = True

        total_first_semester_credit = 0
        total_sec_semester_credit = 0
        total_registered_credit = 0
        for i in courses:
            if i.semester == "First":
                total_first_semester_credit += int(i.credit)
            if i.semester == "Second":
                total_sec_semester_credit += int(i.credit)
        for i in registered_courses:
            total_registered_credit += int(i.credit)
        context = {
            "is_calender_on": True,
            "all_courses_are_registered": all_courses_are_registered,
            "no_course_is_registered": no_course_is_registered,
            "current_semester": current_semester,
            "courses": courses,
            "total_first_semester_credit": total_first_semester_credit,
            "total_sec_semester_credit": total_sec_semester_credit,
            "registered_courses": registered_courses,
            "total_registered_credit": total_registered_credit,
            "student": student,
        }
        return render(request, "course/course_registration.html", context)


@login_required
@student_required
def course_drop(request):
    if request.method == "POST":
        student = get_object_or_404(Student, student__pk=request.user.id)
        course_ids = request.POST.getlist("course_ids")
        print("course_ids", course_ids)
        for course_id in course_ids:
            course = get_object_or_404(Course, pk=course_id)
            TakenCourse.objects.filter(student=student, course=course).delete()
        messages.success(request, "Courses dropped successfully!")
        return redirect("course_registration")


# ########################################################
# User Course List View
# ########################################################


@login_required
def user_course_list(request):
    if request.user.is_lecturer:
        courses = Course.objects.filter(allocated_course__lecturer__pk=request.user.id)
        return render(request, "course/user_course_list.html", {"courses": courses})

    if request.user.is_student:
        student = get_object_or_404(Student, student__pk=request.user.id)
        taken_courses = TakenCourse.objects.filter(student=student)
        return render(
            request,
            "course/user_course_list.html",
            {"student": student, "taken_courses": taken_courses},
        )

    # For other users
    return render(request, "course/user_course_list.html")
