import csv
import json
import random
import os
from .logger import get_logger
from .validators import QuestionValidator
from pathlib import Path

logger = get_logger("questionbank")

class QuestionBank():
    qdir=None
    round1:tuple=tuple()
    round2:tuple=tuple()
    round3:tuple=tuple()
    round4:tuple=tuple()

    def __init__(self, qdir:str) -> None:
        self.qdir = qdir
        if not os.path.exists(self.qdir):
            os.makedirs(self.qdir, exist_ok=True)
            os.makedirs(os.path.join(self.qdir, "imgs"), exist_ok=True)
            
        self.load()
        pass

    def loadQfromCSV(self, csvPath):
        """
        Load questions from CSV file with validation and encoding fallback.
        
        Args:
            csvPath: Path to CSV file
        
        Returns:
            Tuple of Question objects
        """
        allQuestions = list()
        errors = []
        base_path = Path(csvPath).parent / "imgs"
        
        logger.info(f"Loading questions from {csvPath}")
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
        content = None
        successful_encoding = None
        
        for encoding in encodings:
            try:
                with open(csvPath, "r", encoding=encoding) as f:
                    content = f.read()
                    successful_encoding = encoding
                    logger.debug(f"Successfully read CSV with encoding: {encoding}")
                    break
            except (UnicodeDecodeError, LookupError) as e:
                logger.debug(f"Failed to read with {encoding}: {str(e)[:50]}")
                continue
        
        if content is None:
            logger.error(f"Could not read CSV file with any encoding: {csvPath}")
            return tuple()
        
        try:
            # Parse CSV content
            import io
            reader = csv.reader(io.StringIO(content))
            
            for i, row in enumerate(reader):
                if i == 0:
                    # Validate header
                    expected_columns = 5  # qid, text, options, answer, imgPath
                    if len(row) < expected_columns:
                        logger.warning(f"CSV header has {len(row)} columns, expected at least {expected_columns}")
                    continue  # skip header row
                
                # Validate row
                is_valid, error = QuestionValidator.validate_csv_row(row, i, base_path)
                if not is_valid:
                    errors.append(error)
                    logger.warning(f"Skipping invalid row {i}: {error}")
                    continue
                
                try:
                    allQuestions.append(Question(*row))
                except Exception as e:
                    errors.append(f"Row {i}: Error creating question - {e}")
                    logger.warning(f"Error creating question from row {i}: {e}")
            
            if errors:
                logger.warning(f"Found {len(errors)} validation errors in {csvPath}")
                for error in errors[:5]:  # Log first 5 errors
                    logger.warning(f"  - {error}")
                if len(errors) > 5:
                    logger.warning(f"  ... and {len(errors) - 5} more errors")
            
            logger.info(f"Loaded {len(allQuestions)} valid questions from {csvPath} (encoding: {successful_encoding})")
            return tuple(allQuestions)
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csvPath}")
            return tuple()
        except Exception as e:
            logger.error(f"Error loading CSV file {csvPath}: {e}", exc_info=True)
            return tuple()

    def load(self):
        """
        Load all question rounds from CSV files.
        """
        if not os.path.exists(self.qdir):
            logger.error(f"Question directory does not exist: {self.qdir}")
            raise OSError(f"question directory {self.qdir} does not exists")
        
        files = tuple(map(lambda _: os.path.join(self.qdir, _), ("r1.csv", "r2.csv", "r3.csv", "r4.csv")))

        if os.path.exists(files[0]):
            self.round1 = self.loadQfromCSV(files[0])
        else:
            logger.warning(f"Round 1 CSV not found: {files[0]}")
            self.round1 = tuple()
        
        if os.path.exists(files[1]):
            self.round2 = self.loadQfromCSV(files[1])
        else:
            logger.warning(f"Round 2 CSV not found: {files[1]}")
            self.round2 = tuple()
        
        if os.path.exists(files[2]):
            self.round3 = self.loadQfromCSV(files[2])
        else:
            logger.warning(f"Round 3 CSV not found: {files[2]}")
            self.round3 = tuple()
        
        if os.path.exists(files[3]):
            self.round4 = self.loadQfromCSV(files[3])
        else:
            logger.warning(f"Round 4 CSV not found: {files[3]}")
            self.round4 = tuple()

        logger.info(f"Question bank loaded - Round1: {len(self.round1)}, Round2: {len(self.round2)}, "
                   f"Round3: {len(self.round3)}, Round4: {len(self.round4)}")

class Question():
    """Data class for Question"""
    qid:str=None
    imgPath:str=None
    text:str=None
    options:str = None
    answer:int=None

    def __init__(self, qid, text, options, answer, imgPath, *args) -> None:
        self.qid = qid
        self.text = text
        self.options = options
        self.answer = answer
        self.imgPath = imgPath
    
    def forParticipant(self):
        return ClientQuestion(self.qid, self.text, self.options, self.imgPath)
    
class ClientQuestion():
    def __init__(self, qid, text, options, imgPath) -> None:
        self.qid = qid
        self.text = text
        self.options = options
        self.imgPath = imgPath

    def jsons(self):
        return json.dumps({
            "qid":self.qid,
            "text":self.text,
            "options":self.options,
            "imgPath":self.imgPath
        })
    
    def loads(self, s):
        data = json.loads(s)
        self.qid=data.get("qid")
        self.text=data.get("text")
        self.options=str(data.get("options") or "").split("|")
        self.imgPath=data.get("imgPath")
        return self
    
    def optionsT(self):
        # return tuple(filter(bool,self.options.split("|")))
        options_l = list()
        if not self.options:
            return ("", "", "", "")
        values = list(filter(bool, self.options.split("|")))
        try:
            for i in range(4):
                val = values[i] if i < len(values) else ""
                options_l.append(val)
            return tuple(options_l)
        except (IndexError, TypeError) as e:
            logger.warning(f"Error parsing options: {e}, returning empty options")
            return ("", "", "", "")
    
    def get_img_path(self):
        if not self.imgPath: return None
        return os.path.join(os.getcwd(), "data", "questions", "imgs", self.imgPath)
    
