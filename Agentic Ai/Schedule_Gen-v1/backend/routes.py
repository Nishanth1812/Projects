from flask import Blueprint,jsonify,request,render_template
import os 
import logging
import shutil
import tempfile
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from core.document_processor import process_doc
from core.Schedule_generator import parse_preferences,retrieve_tasks,generate_schedule



load_dotenv()
bp=Blueprint('routes',__name__)
logger=logging.getLogger(__name__)


# Upload endpoint
@bp.route('/upload',methods=['POST'])
def upload_files():
    if "file" not in request.files:
        return jsonify({"Error":"No file found"}),400
    
    file=request.files["file"]
    
    if file.filename=="" or not file.filename.lower().endswith(('.pdf', '.docx')): #type: ignore 
        return jsonify({"Error":"Invalid file"}),400
    
    temp_dir=tempfile.mkdtemp() #Creating temp directory 
    
    try:
        fname=secure_filename(filename=file.filename) #type: ignore
        f_path=os.path.join(temp_dir,fname) 
        file.save(f_path)
    
        res=process_doc(f_path,os.path.splitext(f_path)[1].strip("."))
        if res:
            return jsonify({"Message":"Succesfully Processed the document"})
        else:
            return jsonify({"Error": "Document processing failed"}), 500
    except Exception as e:
        return jsonify({"Error":str(e)}),500 
    
    finally:
        shutil.rmtree(temp_dir,ignore_errors=True)
        
        
        



# Task gen endpoint 

CURRENT_SCHEDULE = None

@bp.route('/schedule', methods=['POST'])
def show_schedule():
    """Render the schedule immediately after generation."""
    try:
        data = request.get_json()
        user_input = data.get("prompt", "")
        if not user_input:
            return jsonify({"Error": "No user input"}), 400

        # Run through pipeline
        prefs = parse_preferences(user_input)
        tasks = retrieve_tasks(prefs)
        schedule = generate_schedule(prefs, tasks)

        # Directly render schedule.html with fresh data
        return render_template("schedule.html", schedule=schedule)

    except Exception as e:
        logger.exception(f"Error while generating schedule for UI: {e}")
        return jsonify({"Error": "Failed to generate schedule"}), 500

@bp.route('/feedback', methods=['POST'])
def feedback():
    """Accept user feedback and regenerate schedule."""
    global CURRENT_SCHEDULE
    try:
        data = request.get_json()
        user_feedback = data.get("feedback", "")
        if not user_feedback:
            return jsonify({"Error": "No feedback provided"}), 400

        # For now: re-use existing prefs + tasks, just append feedback
        prefs = parse_preferences(user_feedback)  # lightweight: parse again
        tasks = retrieve_tasks(prefs)
        new_schedule = generate_schedule(prefs, tasks)

        CURRENT_SCHEDULE = new_schedule
        return jsonify({
            "Message": "Schedule regenerated with feedback",
            "Schedule": new_schedule
        })
    except Exception as e:
        logger.exception(f"Error in feedback loop: {e}")
        return jsonify({"Error": "Feedback processing failed"}), 500

