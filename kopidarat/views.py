# Django imports
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.db import connection, IntegrityError
from django.urls import reverse
from django.core.mail import send_mail
from django.template import loader
from dateutil.relativedelta import relativedelta

# Custom imports
import datetime

# View Functions for main pages for the member's side of the website

def index(request,*kwargs):
    '''
    Index view function responsible for the main page of the website.
    Takes in the request and returns the rendering of the main page.
    NOTE: The function for joining events is refactored out for better code clarity. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the main page (path: '') 
    '''
    # Checking if user is logged in
    user_email = request.session.get("email", False)
    message=''
    if kwargs:
        message=''.join(kwargs)
    
    if user_email is not False:
         with connection.cursor() as cursor:
                cursor.execute("SELECT a.activity_id, u.full_name as driver, a.start_point, a.start_date_time, a.destination, count_passenger.count , a.capacity,a.price FROM activity a, users u, joins j, (SELECT j1.activity_id, COUNT(j1.passenger) as count FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id GROUP BY j1.activity_id) AS count_passenger WHERE a.driver = u.email AND j.activity_id = a.activity_id AND j.passenger = u.email AND count_passenger.activity_id = a.activity_id ORDER BY a.start_date_time DESC")
                activities = cursor.fetchall()
                ordering_sql = " ORDER BY a.start_date_time ASC"
                context={'activities':activities}
                return render(request, "index.html", context)
    else:
        return HttpResponseRedirect(reverse("frontpage"))


    

def become_admin(request):
    context = {}
    status = ''

    if request.method == "POST":
        # Ensure password matches confirmation

        
        with connection.cursor() as cursor:
            try:
                cursor.execute("CALL become_admin(%s, %s)", [request.POST['username'], request.POST['reason']])
                request.session["username"] = request.POST['username']
                request.session["email"] = request.POST['email']

                return redirect('index')
            except IntegrityError:
                status = 'There exists a user with the same email or username'
  
    context['message'] = status
    return render(request, "become_admin.html", context)

  

  




def create_activity(request):
    '''
    create_activity view function responsible for the creating activity html page.
    Takes in the request and returns the rendering of the create_activity page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the create_activity page (path: '/create_activity')
    '''
    # Check if user is logged in
    user_email = request.session.get("email", False)

    if user_email is not False:
        # context = {}
        # with connection.cursor() as cursor:
        #     cursor.execute('SELECT * FROM category')
        #     categories = cursor.fetchall()
        #     context["categories"] = categories

        if request.method == 'POST':

            with connection.cursor() as cursor:
                cursor.execute('CALL create_new_activity(%s,%s,%s,%s,%s,%s)',[
                    user_email,request.POST['price'],request.POST['start_point'],request.POST['start_date_time'],request.POST['destination'], request.POST['capacity']])
                return HttpResponseRedirect(reverse("user_activity"))
        else:
            return render(request, 'create_activity.html') # removed context from (request, 'create_activity.html', context)
    return HttpResponseRedirect(reverse("index"))


def join(request, activity_id):
    '''
    join view function that is responsible for the joining button on the main page.
    Takes in the request and the activity_id of the event and executes an SQL statement 
    to insert the user values to the joins table. Returns an http response redirect function.
    Argument:
        request: HTTP request
        activity_id: the activity_id of the associated event
    Return:
        HTTP response redirect to the main page. 
    '''
    user_email = request.session.get("email", False)
    message = ''

    if user_email is not False:

        with connection.cursor() as cursor:
            try:
                cursor.execute('INSERT INTO joins VALUES (%s,%s)', [
                                activity_id, user_email])
                message='You have successfully registered for this activity!'
            except IntegrityError:
                message='You have registered for this activity.'
            except Exception:
                message='We regret to inform you that the activity has reached its maximum capacity.'
            
    return index(request,message)

def user_activity(request):
    '''
    user_activity view function that is responsible for the user_activity page.
    Takes in the request and the username of the user and returns the rendering 
    of the user_activity page. 
    # NOTE: the function for deleting and updating events is refactored out for better code clarity. 
    Argument:
        request: HTTP request
    Return: 
        render function: renders the user_activity page
    '''
    user_email = request.session.get("email", False)
    
    if user_email is not False:

        # need a dictionary to store some of the information that is needed to be passed to the html pages
        context = dict()
        inviter_past_list_empty=True
        inviter_future_list_empty=True
        joined_future_activities_list_empty=True
        joined_past_activities_list_empty=True
        reports_list_empty=True
        reviews_list_empty=True

        with connection.cursor() as cursor:

            # Get the table of past activities where the current user is the inviter
            cursor.execute('SELECT * FROM activity a, users u WHERE a.driver = u.email AND a.driver = %s AND a.start_date_time < NOW() ORDER BY a.start_date_time ASC', [
                user_email
            ])
            past_inviter_list = cursor.fetchall()
            if len(past_inviter_list)>0:
                inviter_past_list_empty=False
            if inviter_past_list_empty:
                context["inviter_past_list_empty"]=inviter_past_list_empty

            # Get the table of upcoming activities where the current user is the inviter
            cursor.execute('SELECT a.activity_id, u.full_name as driver, a.price, a.start_point, a.start_date_time, a.destination, count_passenger.count, a.capacity FROM activity a, users u, joins j, (SELECT j1.activity_id, COUNT(j1.passenger) as count FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id GROUP BY j1.activity_id) AS count_passenger WHERE a.driver = u.email AND a.driver = %s AND j.activity_id = a.activity_id AND j.passenger = u.email AND count_passenger.activity_id = a.activity_id AND a.start_date_time > NOW() ORDER BY a.start_date_time ASC', [
                user_email
            ])
            inviter_list = cursor.fetchall()
            if len(inviter_list)>0:
                inviter_future_list_empty=False
            if inviter_future_list_empty:
                context["inviter_future_list_empty"]=inviter_future_list_empty

            # Get the table of upcoming activities created by other user where the user has signed up for
            cursor.execute('SELECT DISTINCT a.activity_id, u.full_name, a.price, a.start_point, a.start_date_time, a.destination, count_passenger.count, a.capacity FROM joins j, activity a, users u, (SELECT j1.activity_id, COUNT(j1.passenger) as count FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id GROUP BY j1.activity_id) AS count_passenger WHERE a.driver = u.email AND a.driver<>%s AND count_passenger.activity_id = a.activity_id AND j.passenger = %s AND j.activity_id = a.activity_id AND NOW() <= a.start_date_time ORDER BY a.start_date_time ASC', [user_email,user_email])
            
            upcoming_activities_list = cursor.fetchall()
            if len(upcoming_activities_list)>0:
                joined_future_activities_list_empty=False
            if joined_future_activities_list_empty:
                context["joined_future_activities_list_empty"]=joined_future_activities_list_empty

            # Get the table of past activities created by other user where the user has joined
            cursor.execute('SELECT a.activity_id, a.driver, u.full_name, a.price, a.start_point, a.start_date_time,  a.destination FROM joins j, activity a, users u WHERE j.activity_id = a.activity_id AND a.driver = u.email AND a.driver <> j.passenger AND j.passenger = %s AND NOW() > a.start_date_time ORDER BY a.start_date_time ASC', [
                user_email
            ])
            joined_activities_list = cursor.fetchall()
            if len(joined_activities_list)>0:
                joined_past_activities_list_empty=False
            if joined_past_activities_list_empty:
                context["joined_past_activities_list_empty"]=joined_past_activities_list_empty
            

            # Get table of reviews that user has created
            cursor.execute('SELECT r.timestamp, a.start_point, r.rating, r.comment FROM review r, activity a, users u WHERE r.activity_id = a.activity_id AND r.passenger = u.email AND r.passenger = %s ORDER BY a.start_date_time ASC', [
                user_email
            ])
            reviews_list = cursor.fetchall()
            if len(reviews_list)>0:
                reviews_list_empty=False
            if reviews_list_empty:
                context["reviews_list_empty"]=reviews_list_empty

            # Get table of reports that user has created
            cursor.execute('SELECT r.timestamp, r.report_user, r.comment, r.severity FROM report r, users u WHERE r.report_user = u.email AND r.submitter = %s ORDER BY r.timestamp ASC', [
                user_email
            ])
            reports_list = cursor.fetchall()
            if len(reports_list)>0:
                reports_list_empty=False
            if reports_list_empty:
                context["reports_list_empty"]=reports_list_empty

        context['user_fullname'] = request.session.get('full_name')
        context['inviter_past_list'] = past_inviter_list
        context['inviter_future_list'] = inviter_list
        context['joined_future_activities_list'] = upcoming_activities_list
        context['joined_past_activities_list'] = joined_activities_list
        context['reviews_list'] = reviews_list
        context['reports_list'] = reports_list

        return render(request, 'user_activity.html', context)

    else:
        return HttpResponseRedirect(reverse("index"))

def update_activity(request, activity_id):
    '''
    update_activity view function responsible for the update activity page.
    Takes in the request and activity_id of the event and returns a render function
    that renders the update_activity page. Executes SQL statement to update the values
    inside the activity table.
    Argument:
        request: HTTP request
        activity_id: the activity id of the event
    Return: 
        render function: renders the update activity page (path: /update_activity)
    '''
    user_email = request.session.get("email", False)
    context={}

    if user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM activity WHERE activity_id=%s', [activity_id])
            this_activity = cursor.fetchone()

        if request.method == 'POST':  # TODO: catch error when there's no post method, e.g. cancel to create activity
            with connection.cursor() as cursor:

                # Execute SQL query to update the values for the particular instance
                cursor.execute('UPDATE activity SET start_point = %s, price = %s, start_date_time = %s, destination = %s, capacity = %s WHERE activity_id = %s', [
                    request.POST['start_point'], request.POST['price'], request.POST[
                        'start_date_time'], request.POST['destination'], request.POST['capacity'], activity_id
                ])
                cursor.execute('SELECT * FROM activity WHERE activity_id=%s', [activity_id])
                this_activity = cursor.fetchone()
            return HttpResponseRedirect(reverse("user_activity"))

        context['this_activity'] = this_activity
        return render(request,'admin_activity_edit.html',context)

    return HttpResponseRedirect(reverse("index"))


def delete_activity(request, activity_id):
    '''
    delete_activity view function which is responsible for the delete button 
    in the user_activity page. Takes in the request and activity_id of the event
    and executes a SQL statement to delete the activity from the user's display.
    Argument: 
        request: HTTP request
        activity_id: the activity_id of the event
    Return:
        HTTP Response Redirect to the main page
    '''
    user_email = request.session.get("email", False)

    if user_email is not False:
        with connection.cursor() as cursor:

            # Execute SQL query to delete the user from joining the activity
            cursor.execute('DELETE FROM joins WHERE activity_id = %s AND passenger = %s', [
                activity_id, request.session.get('email')
            ])
        return HttpResponseRedirect(reverse("user_activity"))
    else:
        return HttpResponseRedirect(reverse("index"))


def passenger(request, activity_id):
    """ 
    View function that enables people who have signed up in the activity to view everyone else who signed up.
    Takes in the request and activity_id of the event and returns a render function that renders the 
    participants page. 
    Arguments:
        request: HTTP request
        activity_id: activity_id of the event
    Return:
        render function: render the participants page (path: /participants/<activity_id>)
    """
    # context dicitonary to store the values
    context = {}
    user_email = request.session.get("email", False)
   

    if user_email is not False:

        with connection.cursor() as cursor:
            # Execute SQL query to check if user is registered under this activity
            cursor.execute('SELECT * FROM joins WHERE activity_id=%s AND passenger=%s', [
                activity_id, user_email
            ])
            user = cursor.fetchone()

        if user is not None:
            with connection.cursor() as cursor:
                cursor.execute("SELECT u.full_name, u.username, u.email, u.phone_number, (CASE WHEN u.email=a.driver THEN 'Driver' ELSE 'Passenger' END) AS remarks FROM users u, joins j, activity a WHERE j.activity_id = a.activity_id AND j.activity_id=%s AND u.email=j.passenger AND u.email<>%s",
                            [int(activity_id), user_email])
                passenger = cursor.fetchall()

                cursor.execute(
                    'SELECT a.start_point,a.driver FROM activity a WHERE a.activity_id=%s', [activity_id])
                start_point, driver, = cursor.fetchone()

                

           
            context["passenger"] = passenger
            context["start_point"] = start_point
            context["driver"] = driver
            return render(request, 'passenger.html', context)
        else:
            message="You are not registered for this activity, hence you are not authorised to view this page."
            request.session['message'] = message
            return HttpResponseRedirect('/all_activities')


def create_review(request,activity_id):
    '''
    create_review view function which is responsible for the creating review page.
    Takes in the request and returns a render function to render the review page.
    Argument: 
        request: HTTP request
    Return: 
        render function: renders the review page (path: /create_review)
    '''
    user_email = request.session.get("email", False)
    message = ""
    context={}
    if user_email is not False:
        with connection.cursor() as cursor:
            cursor.execute('SELECT u.full_name AS name, a.start_point AS start_point FROM activity a, users u WHERE a.activity_id=%s AND u.email=a.driver',[activity_id])
            activity_details = cursor.fetchone()
            context["activity_details"]=activity_details
            if request.method == 'POST':
                cursor.execute('INSERT INTO review VALUES (%s,%s,%s,%s,%s)', [
                    request.POST['activity_id'], datetime.datetime.now(
                    ), user_email,request.POST['rating'],request.POST['comment']])

        context["message"]=message
        return render(request, 'review.html',context)
    else:
        return HttpResponseRedirect(reverse("index"))


def create_report(request):
    '''
    create_report view function which is responsible for the reports page.
    Takes in the request and returns a render function to render the reports page.
    Argument: 
        request: HTTP request
    Return:
        render function: renders the reports page (path: /create_report)
    '''
    user_email = request.session.get("email", False)
    message = ""

    if user_email is not False:
        if request.method == 'POST':

            with connection.cursor() as cursor:
                try:
                    cursor.execute('INSERT INTO report VALUES (%s,%s,(SELECT email FROM users WHERE username=%s),%s,%s)', [
                        user_email, datetime.datetime.now(), request.POST['username'],
                        request.POST['comment'], request.POST['severity']])
                except IntegrityError:
                    message = 'There exists no user with the username '+request.POST['username']+'. Please try again.'
        return render(request, 'report.html', {"message": message})
    else:
        return HttpResponseRedirect(reverse("index"))

# View functions for the admin side of the website


def admin_index(request):
    '''
    index_admin view function that is responsible for the rendering of the administrator's page.
    Takes in a request and returns the rendering of the administrator's page.
    Argument:
        request: HTTP request
    Return:
        render function: renders the administrator's main page (path: /admin_index)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        # dictionary to store all the values
        context = dict()

        with connection.cursor() as cursor:
            
            cursor.execute(
                'SELECT * FROM requests')
            list_of_requests = cursor.fetchall()


            cursor.execute('SELECT * FROM activity')
            activities = cursor.fetchall()
            ordering_sql = " ORDER BY a.start_date_time ASC"

        context = {
            'activities': activities,
            'list_of_requests':list_of_requests
        }
        return render(request, 'admin_index.html', context)
    else:
        return HttpResponseRedirect(reverse('login'))


def admin_user(request):
    '''
    user_admin view function responsible for the list of users page from the admin side.
    Takes in the request and returns the rendering of the admin_user page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user page (path: /admin_user)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        # TODO: Make a CRUD for the admin site
        with connection.cursor() as cursor:
            # Get the list of users
            # Find out last activity of users
            cursor.execute(
                'SELECT * FROM users ORDER BY type ASC, full_name ASC')
            list_of_users = cursor.fetchall()

        context['list_of_users'] = list_of_users

        return render(request, 'admin_user.html', context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))


def admin_user_create(request):
    '''
    admin_user_create view function responsible for the creation of users from the admin side.
    Takes in the request and returns the rendering of the admin_user_create page.
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user_create page (path: /admin_user_create)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    context = dict()
    message = ''

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                created_user_type = request.POST['type']

                cursor.execute('INSERT INTO users (full_name,username,email,phone_number,password,type) VALUES (%s,%s,%s,%s,%s,%s)', [
                    request.POST['full_name'], request.POST['username'], request.POST[
                        'email'], request.POST['phone_number'], request.POST['password'], request.POST['type']
                ])

                if created_user_type == 'member':
                    cursor.execute('INSERT INTO member (email) VALUES (%s)', [
                                   request.POST['email']])
                elif created_user_type == 'administrator':
                    cursor.execute('INSERT INTO administrator (email) VALUES (%s)', [
                                   request.POST['email']])
                else:
                    message = 'Please indicate a right user type'

        context['message'] = message
        return render(request, 'admin_user_create.html', context)

    return HttpResponseRedirect(reverse('admin_index'))


def admin_user_edit(request, edit_email):
    '''
    admin_user_edit view function responsible for the editing of user's credentials from the admin side.
    Takes in the request and the user's email and returns the rendering of the admin_user_edit page.
    Argument:
        request: HTTP request
        edit_email: user email that wants to be edited
    Return:
        render function: renders the admin_user_edit page (path: /admin_user_edit/edit_email)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')
    context = {}

    if user_type == 'administrator' and user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM users WHERE email = %s', [edit_email])
            obj = cursor.fetchone()

        if request.method == 'POST':
            with connection.cursor() as cursor:

                cursor.execute('UPDATE users SET full_name = %s, username = %s, phone_number = %s, password = %s, type = %s WHERE email = %s', [
                    request.POST['full_name'], request.POST['username'], request.POST[
                        'phone_number'], request.POST['password'], request.POST['type'], edit_email
                ])
                cursor.execute(
                    'SELECT * FROM users WHERE email = %s', [edit_email])
                obj = cursor.fetchone()

            return HttpResponseRedirect(reverse('admin_user'))

        # else:
            # return render(request,'admin_user_edit.html',context)

        context['obj'] = obj
        return render(request, 'admin_user_edit.html', context)

    return HttpResponseRedirect(reverse('admin_index'))


def admin_user_delete(request, delete_email):
    '''
    admin_user_delete view function responsible for the deleting users from the database from the admin side.
    Takes in the request and the user's email and executes a SQL query to delete the user from the database.
    Argument:
        request: HTTP request
        delete_email: user email that wants to be deleted
    Return: 
        HTTP Response Redirect to the admin_user page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute(
                    'SELECT type FROM users WHERE email = %s', [delete_email])
                delete_type = cursor.fetchone()

                # check which type, to correctly initiate the ON DELETE CASCADE
                # also check so that the admin does not delete him/herself
                if delete_type == 'administrator' and user_email != delete_email:
                    cursor.execute(
                        'DELETE FROM administrator WHERE email = %s', [delete_email])
                    # TODO: pops up the message if the admin is trying to delete him/herself
                elif delete_type == 'member':
                    cursor.execute(
                        'DELETE FROM member WHERE email = %s', [delete_email])

        return HttpResponseRedirect(reverse('admin_user'))

    return HttpResponseRedirect(reverse('admin_index'))


def admin_activity(request):
    '''
    admin_activity view function responsible for the list of activities page from the admin side.
    Takes in the request and returns the rendering of the admin_activity page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_activity page (path: /admin_activity)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()
        with connection.cursor() as cursor:
            cursor.execute('SELECT a.activity_id, u.full_name as driver, a.price, a.start_point, a.start_date_time, a.destination, count_passenger.count, a.capacity FROM activity a, users u, joins j, (SELECT j1.activity_id, COUNT(j1.passenger) as count FROM activity a1, joins j1 WHERE j1.activity_id = a1.activity_id GROUP BY j1.activity_id) AS count_passenger WHERE a.driver = u.email AND j.activity_id = a.activity_id AND j.passenger = u.email AND count_passenger.activity_id = a.activity_id AND count_passenger.count <= a.capacity GROUP BY a.activity_id, u.full_name, a.price, a.start_point, a.start_date_time, a.destination, count_passenger.count, a.capacity ORDER BY a.start_date_time ASC')
            activities = cursor.fetchall()
            context['activities'] = activities
            return render(request, 'admin_activity.html', context)
           
    else:
        return HttpResponseRedirect(reverse('admin_index'))

def admin_activity_create(request):
    '''
    admin_activity_create view function responsible for the creation of activity from the admin side.
    Takes in the request and returns the rendering of the admin_activity_create page.
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_user_create page (path: /admin_activity_create)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM category')
            categories = cursor.fetchall()

        if request.method == 'POST':

            with connection.cursor() as cursor:

                # TODO: Add the checking of inputs
                # Insert the activity into the database
                cursor.execute('INSERT INTO activity (driver,activity_name,category,start_date_time,venue,capacity) VALUES (%s,%s,%s,%s,%s,%s)', [
                    request.session.get(
                        "email"), request.POST['activity_name'], request.POST['category'], request.POST['start_date_time'],
                    request.POST['venue'], request.POST['capacity']
                ])
                # Get the activity details
                cursor.execute('SELECT activity_id FROM activity WHERE driver =  %s AND activity_name = %s AND category = %s AND start_date_time = %s AND venue = %s AND capacity = %s', [
                    request.session.get(
                        "email"), request.POST['activity_name'], request.POST['category'], request.POST['start_date_time'],
                    request.POST['venue'], request.POST['capacity']
                ])
                activity_id = cursor.fetchone()
                # Joining the current user to the joins database
                cursor.execute('INSERT INTO joins VALUES (%s,%s)', [
                    activity_id, request.session.get("email")
                ])

            return HttpResponseRedirect(reverse('admin_activity'))

        context = {'categories': categories}
        return render(request, 'admin_activity_create.html', context)

    return HttpResponseRedirect(reverse('admin_activity'))

def admin_activity_edit(request, activity_id):
    '''
    admin_activity_edit view function responsible for the editing of activity from the admin side.
    Takes in the request and the user's email and returns the rendering of the admin_activity_edit page.
    Argument:
        request: HTTP request
        activity_id: activity_id that wants to be edited
    Return:
        render function: renders the admin_user_edit page (path: /admin_activity_edit/activity_id)
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')
    context = {}

    if user_type == 'administrator' and user_email is not False:

        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM activity WHERE activity_id=%s', [activity_id])
            this_activity = cursor.fetchone()

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('UPDATE activity SET category = %s, activity_name = %s, start_date_time = %s, venue = %s, capacity = %s WHERE activity_id = %s', [
                    request.POST['category'], request.POST['activity_name'], request.POST[
                        'start_date_time'], request.POST['venue'], request.POST['capacity'], activity_id
                ])
                cursor.execute('SELECT * FROM activity WHERE activity_id=%s', [activity_id])
                this_activity = cursor.fetchone()

            return HttpResponseRedirect(reverse('admin_activity'))

        # else:
            # return render(request,'admin_activity_edit.html', context)
        context['this_activity'] = this_activity
        return render(request,'admin_activity_edit.html',context)

    return HttpResponseRedirect(reverse('admin_index'))


def admin_activity_delete(request, activity_id):
    '''
    admin_activity_delete view function responsible for the deleting activities from the database from the admin side.
    Takes in the request and the activity ID and executes a SQL query to delete the user from the database.
    Argument:
        request: HTTP request
        activity_id: activity ID that wants to be deleted
    Return:
        HTTP Response Redirect to the admin_activity page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute(
                    'DELETE FROM activity WHERE activity_id = %s', [activity_id])

        return HttpResponseRedirect(reverse('admin_activity'))

    return HttpResponseRedirect(reverse('admin_index'))


def admin_review(request):
    '''
    user_review view function responsible for the list of reviews page from the admin side.
    Takes in the request and returns the rendering of the admin_review page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_review page (path: /admin_review)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        with connection.cursor() as cursor:
            # Get the list of users
            cursor.execute('SELECT * FROM review')
            list_of_reviews = cursor.fetchall()

        context['list_of_reviews'] = list_of_reviews

        return render(request, 'admin_review.html', context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))


def admin_review_delete(request, activity_id, timestamp, passenger_email):
    '''
    admin_review_delete view function responsible for the deleting reviews from the database from the admin side.
    Takes in the request and the activity ID and executes a SQL query to delete the review from the database.
    Argument:
        request: HTTP request
        activity_id: activity ID of the review that wants to be deleted
        timestamp: timestamp of the review that wants to be deleted
        passenger_email: passenger of the review that wants to be deleted
    Return:
        HTTP Response Redirect to the admin_review page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('DELETE FROM review WHERE activity_id = %s AND timestamp = %s AND passenger = %s', [
                    activity_id, timestamp, passenger_email])

        return HttpResponseRedirect(reverse('admin_review'))

    return HttpResponseRedirect(reverse('admin_index'))


def admin_report(request):
    '''
    user_report view function responsible for the list of reports page from the admin side.
    Takes in the request and returns the rendering of the admin_report page. 
    Argument:
        request: HTTP request
    Return:
        render function: renders the admin_report page (path: /admin_report)
    '''
    user_email = request.session.get("email", False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        context = dict()

        with connection.cursor() as cursor:
            # Get the list of users
            cursor.execute('SELECT * FROM report')
            list_of_reports = cursor.fetchall()

        context['list_of_reports'] = list_of_reports

        return render(request, 'admin_report.html', context)
    else:
        return HttpResponseRedirect(reverse('admin_index'))


def admin_report_delete(request, submitter_email, timestamp):
    '''
    admin_report_delete view function responsible for the deleting reports from the database from the admin side.
    Takes in the request, submitter's email, and timestamp, and executes a SQL query to delete the report from the database.
    Argument:
        request: HTTP request
        submitter_email: the report submitter's email that wants to be deleted
        timestamp: the timestamp of the report that wants to be deleted
    Return:
        HTTP Response Redirect to the admin_report page
    '''
    user_email = request.session.get('email', False)
    user_type = request.session.get('type')

    if user_type == 'administrator' and user_email is not False:

        if request.method == 'POST':

            with connection.cursor() as cursor:

                cursor.execute('DELETE FROM report WHERE submitter = %s AND timestamp = %s', [
                               submitter_email, timestamp])

        return HttpResponseRedirect(reverse('admin_report'))

    return HttpResponseRedirect(reverse('admin_index'))

# View function for category popularity list


def frontpage(request):
    '''
    frontpage view function is a friendly front page for the website
    that introduces a little of what KopiDarat is about and displays 
    general stats of the website to get new visitors interested,
    from the number of activities, number of registered users,
    and the list of activity categories with its respective popularity
    Argument:
        request: HTTP request
    Return:
        render function: renders the category_popularity page (path: /category_popularity)
    '''
    user_email = request.session.get("email", False)
    if user_email is not False:
        return HttpResponseRedirect(reverse('index'))
    context = {}
    with connection.cursor() as cursor:
        cursor.execute('SELECT COUNT(*) FROM activity')
        activity_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
#         cursor.execute(
#             'SELECT category, COUNT(*) FROM activity GROUP BY category ORDER BY COUNT(*) DESC')
#         categories = cursor.fetchall()

        context["activity_count"] = activity_count
        context["user_count"] = user_count
#         context["categories"] = categories
        return render(request, 'frontpage.html', context)


# View functions for login functions
def login_view(request):
    # Check if user is already signed in
    if request.session.get("email", False) is not False:
        return HttpResponseRedirect(reverse("index"))

    if request.method == "POST":
        # Attempt to sign user in
        user_id = request.POST["user_id"]
        password = request.POST["password"]
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT * FROM users WHERE email=%s AND password=%s', [user_id, password])
            user1 = cursor.fetchone()
            cursor.execute(
                'SELECT * FROM users WHERE username=%s AND password=%s', [user_id, password])
            user2 = cursor.fetchone()

        if user1 is not None or user2 is not None:

            # User logged in by email
            if user1 is not None:
                request.session["email"] = user_id
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT username,full_name,type FROM users WHERE email = %s', [user_id])
                    username, full_name, type = cursor.fetchone()
                    request.session["username"] = username
                    request.session["full_name"] = full_name
                    request.session["type"] = type

            # User logged in by username
            else:
                request.session["username"] = user_id
                with connection.cursor() as cursor:
                    cursor.execute(
                        'SELECT email,full_name,type FROM users WHERE username = %s', [user_id])
                    email, full_name, type = cursor.fetchone()
                    request.session["email"] = email
                    request.session["full_name"] = full_name
                    request.session["type"] = type

            if request.session["type"] == 'administrator':
                return HttpResponseRedirect(reverse("admin_index"))
            else:
                return HttpResponseRedirect(reverse("index"))

        # No matching user-password combination found
        else:
            return render(request, "login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "login.html", {"message": "Please login to view our site."})


def logout_view(request):
    if "email" in request.session:
        del request.session["email"]
    return HttpResponseRedirect(reverse("frontpage"))


def register(request):
    context = {}
    status = ''

    if request.method == "POST":
        # Ensure password matches confirmation
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "register.html", {
                "message": "Passwords must match."
            })
        
        with connection.cursor() as cursor:
            try:
                cursor.execute("CALL add_new_member(%s, %s, %s, %s, %s)", [request.POST['full_name'], request.POST['username'], request.POST['email'],request.POST['phone_number'], request.POST['password']])
                request.session["email"] = request.POST['email']
                request.session["full_name"] = request.POST['full_name']
                request.session["type"] = 'member'
                return redirect('index')
            except IntegrityError:
                status = 'There exists a user with the same email or username'
  
    context['message'] = status
    return render(request, "register.html", context)


def forget_password(request):
    if request.method == "POST":
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM user WHERE email = %s",
                           [request.POST['email']])
            user_fullname = cursor.fetchone()
            if user_fullname == None:
                return render(request, "forget_password.html",
                              {"message": "The given email is not registered under any account."})
            else:
                html_message = loader.render_to_string('reset_password_email.html',
                                                       {'full_name': user_fullname})
                send_mail(subject="KopiDarat Account Password Reset",
                          message="Looks like you've forgotten your KopiDarat password! To reset your password, follow the link below:",
                          recipient_list=[request.post['email'], ],
                          fail_silently=False, html_message=html_message)
                return render(request, "reset_password_email_sent.html")
    return render(request, "forget_password.html")


def reset_password(request):
    if request.method == "POST":
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]
        if password != confirmation:
            return render(request, "reset_password.html", {
                "message": "Passwords must match."
            })

        with connection.cursor() as cursor:
            cursor.execute("UPDATE user SET password=%s WHERE email=%s", [
                           request.POST['password'], request.user.email])
            return render(request, "reset_password_successful.html")
    return render(request, "reset_password.html")
