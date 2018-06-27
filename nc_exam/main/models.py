from django.db import models
from datetime import date

# Create your models here.
class Department(models.Model):
    dep_id = models.IntegerField(primary_key=True)
    dep_name = models.CharField(max_length=50)
    level = models.IntegerField()

    def __str__(self):
        return self.dep_name
    
    class Meta:
        db_table = 'Department'

class WorkType(models.Model):
    work_type_id = models.IntegerField(db_column='id', primary_key=True)
    type_name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'WorkType'

class Position(models.Model):
    position_id = models.AutoField(db_column='position_id', primary_key=True)
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'Position'

class Members(models.Model):
    name = models.CharField(max_length=20)
    #dep_id = models.IntegerField()
    verified = models.BooleanField()
    deleted = models.BooleanField()
    intro = models.TextField()
    phone_number = models.CharField(max_length=20)
    weixin_open_id = models.CharField(max_length=50)
    dep_id = models.ForeignKey(Department, on_delete=models.CASCADE, db_column='dep_id')
    #work_type_id = models.IntegerField()
    work_type_id = models.ForeignKey(WorkType, on_delete=models.CASCADE, db_column='work_type_id')
    idcard = models.CharField(primary_key=True, max_length=18)
    position_id = models.ForeignKey(Position, on_delete=models.CASCADE, db_column='position_id')

    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'Members'

class PaperTypes(models.Model):
    type_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=200)

    def __str__():
        return self.name

    class Meta:
        db_table = 'PaperTypes'

class Papers(models.Model):
    paper_id = models.IntegerField(primary_key=True)
    paper_name = models.CharField(max_length=200)
    type_id = models.ForeignKey(PaperTypes, on_delete=models.CASCADE, db_column='type_id')
    work_type_id = models.ForeignKey(WorkType, on_delete=models.CASCADE, db_column='work_type_id')
    set_date = models.DateField(default=date.today)
    passing_score = models.IntegerField()
    test_time = models.IntegerField()

    def __str__():
        return self.paper_name

    class Meta:
        db_table = 'Papers'

class TestPapers(models.Model):
    test_paper_id = models.AutoField(primary_key=True)
    paper_id = models.ForeignKey(Papers, on_delete=models.CASCADE, db_column='paper_id')
    date_time = models.DateTimeField()
    score = models.IntegerField()
    if_exam = models.BooleanField()
    weixin_open_id = models.ForeignKey(Members, to_field='weixin_open_id', on_delete=models.CASCADE, db_column='weixin_open_id')

    def __str__():
        return 'The test id is:' + str(test_paper_id)

    class Meta:
        db_table = 'TestPapers'

class ExamPapers(models.Model):
    exam_paper_id = models.AutoField(primary_key=True)
    paper_ids = models.CharField(max_length=500)
    date_time = models.DateTimeField()
    done_date = models.DateTimeField()
    score = models.FloatField()
    weixin_open_id = models.ForeignKey(Members, on_delete=models.CASCADE, db_column='weixin_open_id')
    done = models.BooleanField()
    exam_time = models.IntegerField()
    passing_score = models.IntegerField()
    name = models.CharField(max_length=100)
    ss_count = models.IntegerField()
    ms_count = models.IntegerField()
    jm_count = models.IntegerField()

    def __str__():
        return self.name

    class Meta:
        db_table = 'ExamPapers'

class Questions(models.Model):
    question_id = models.IntegerField(primary_key=True)
    question_title = models.CharField(max_length=255)
    question_type = models.IntegerField()
    question_answer_texts = models.CharField(max_length=500)
    question_right_answers = models.CharField(max_length=20)
    paper_id = models.ForeignKey(Papers, on_delete=models.CASCADE, db_column='paper_id')
    question_sn = models.IntegerField()

    def __str__():
        return 'The question id is:' + str(question_id)

    class Meta:
        db_table = 'Questions'

class TestQuestions(models.Model):
    test_question_id = models.IntegerField(primary_key=True)
    question_id = models.ForeignKey(Questions, on_delete=models.CASCADE, db_column='question_id')
    answers = models.CharField(max_length=255)
    test_paper_id = models.ForeignKey(TestPapers, on_delete=models.CASCADE, db_column='test_paper_id')
    score = models.FloatField()
    sn = models.IntegerField()

    def __st__():
        return 'The question id is:' + str(test_question_id)

    class Meta:
        db_table = 'TestQuestions'

class ExamQuestions(models.Model):
    exam_question_id = models.AutoField(primary_key=True)
    question_id = models.ForeignKey(Questions, on_delete=models.CASCADE, db_column='question_id')
    answers = models.CharField(max_length=255)
    exam_paper_id = models.ForeignKey(ExamPapers, on_delete=models.CASCADE, db_column='test_paper_id')
    score = models.FloatField()
    sn = models.IntegerField()

    def __st__():
        return 'The question id is:' + str(exam_question_id)

    class Meta:
        db_table = 'ExamQuestions'
