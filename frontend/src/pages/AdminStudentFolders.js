import { useState, useEffect, useRef } from 'react';
import { studentsAPI, getErrorMessage } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Folder, 
  FolderOpen, 
  ChevronRight, 
  ArrowLeft, 
  Move, 
  Trash2, 
  Eye, 
  StickyNote, 
  Upload, 
  Search, 
  Users, 
  FileSpreadsheet,
  Grid,
  CheckCircle2,
  ArrowRight,
  Pencil
} from 'lucide-react';

const AdminStudentFolders = () => {
  // Navigation & Tree state
  const [level, setLevel] = useState('departments'); // 'departments' | 'years' | 'students'
  const [selectedDept, setSelectedDept] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null);
  const [folderTree, setFolderTree] = useState([]);
  const [loadingTree, setLoadingTree] = useState(true);

  // Student list state (for current folder)
  const [students, setStudents] = useState([]);
  const [loadingStudents, setLoadingStudents] = useState(false);

  // Global search & index state
  const [allStudents, setAllStudents] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const searchContainerRef = useRef(null);

  // Selection & Highlight state
  const [checkedIds, setCheckedIds] = useState([]);
  const [highlightedStudentId, setHighlightedStudentId] = useState(null);

  // Dialog states
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showNoteDialog, setShowNoteDialog] = useState(false);
  const [noteStudent, setNoteStudent] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [uploading, setUploading] = useState(false);
  const [uploadDept, setUploadDept] = useState('');
  const [uploadYear, setUploadYear] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadStep, setUploadStep] = useState(1); // 1=Select Dept/Year, 2=Upload File, 3=Review

  // Move dialog state
  const [showMoveDialog, setShowMoveDialog] = useState(false);
  const [moveTargetIds, setMoveTargetIds] = useState([]);
  const [moveDept, setMoveDept] = useState('IT');
  const [moveYear, setMoveYear] = useState('1');

  // Edit dialog state
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editStudent, setEditStudent] = useState(null);
  const [editFormData, setEditFormData] = useState({
    roll_number: '',
    full_name: '',
    department: '',
    year: '',
    dob: '',
    email: '',
    phone_number: ''
  });
  const [editSaving, setEditSaving] = useState(false);

  // Rename folder (dept/year card) state
  const [showRenameDialog, setShowRenameDialog] = useState(false);
  const [renameMode, setRenameMode] = useState('dept'); // 'dept' | 'year'
  const [renamingDept, setRenamingDept] = useState('');
  const [renamingYear, setRenamingYear] = useState('');
  const [renameNewDept, setRenameNewDept] = useState('');
  const [renameNewYear, setRenameNewYear] = useState('');
  const [renameSaving, setRenameSaving] = useState(false);
  // List of standard options for move dropdown
  const DEPARTMENTS = ['IT', 'CSE', 'ECE', 'EEE', 'MECH', 'CIVIL'];
  const YEARS = ['1', '2', '3', '4'];

  useEffect(() => {
    fetchInitialData();

    // Click outside handler for search dropdown
    const handleClickOutside = (event) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setShowSearchDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchInitialData = async () => {
    setLoadingTree(true);
    try {
      const treeResp = await studentsAPI.getFolderTree();
      setFolderTree(treeResp.data);

      const allResp = await studentsAPI.getStudents();
      setAllStudents(allResp.data);
    } catch (error) {
      console.error('Failed to fetch initial data:', error);
      toast.error('Failed to load student directory');
    } finally {
      setLoadingTree(false);
    }
  };

  const fetchFolderStudents = async (dept, yr) => {
    setLoadingStudents(true);
    setCheckedIds([]);
    try {
      const response = await studentsAPI.getByFolder(dept, yr);
      setStudents(response.data);
    } catch (error) {
      console.error('Failed to fetch students for folder:', error);
      toast.error('Failed to load students in this folder');
    } finally {
      setLoadingStudents(false);
    }
  };

  // Format Year display
  const formatYear = (yr) => {
    if (yr === '1') return '1st Year';
    if (yr === '2') return '2nd Year';
    if (yr === '3') return '3rd Year';
    if (yr === '4') return '4th Year';
    return yr.endsWith('Year') || yr.endsWith('year') ? yr : `${yr} Year`;
  };

  // Group folder tree by Department
  const getDepartments = () => {
    const depts = {};
    folderTree.forEach(item => {
      if (!depts[item.department]) {
        depts[item.department] = {
          name: item.department,
          studentCount: 0,
          years: []
        };
      }
      depts[item.department].studentCount += item.count;
      depts[item.department].years.push({
        year: item.year,
        count: item.count
      });
    });
    return Object.values(depts).sort((a, b) => a.name.localeCompare(b.name));
  };

  // Get years for selected department
  const getYearsForDept = (deptName) => {
    const dept = folderTree.filter(item => item.department === deptName);
    return dept.sort((a, b) => a.year.localeCompare(b.year));
  };

  // Navigation handlers
  const handleDeptClick = (deptName) => {
    setSelectedDept(deptName);
    setLevel('years');
  };

  const handleYearClick = (yr) => {
    setSelectedYear(yr);
    setLevel('students');
    fetchFolderStudents(selectedDept, yr);
  };

  const navigateToDepartments = () => {
    setSelectedDept(null);
    setSelectedYear(null);
    setLevel('departments');
    setStudents([]);
    setCheckedIds([]);
  };

  const navigateToYears = () => {
    setSelectedYear(null);
    setLevel('years');
    setStudents([]);
    setCheckedIds([]);
  };

  // Global search implementation
  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);

    if (query.trim().length > 1) {
      const filtered = allStudents.filter(student =>
        student.full_name.toLowerCase().includes(query.toLowerCase()) ||
        student.roll_number.toLowerCase().includes(query.toLowerCase()) ||
        student.email.toLowerCase().includes(query.toLowerCase()) ||
        student.department.toLowerCase().includes(query.toLowerCase())
      );
      setSearchResults(filtered.slice(0, 10)); // limit to 10 results
      setShowSearchDropdown(true);
    } else {
      setSearchResults([]);
      setShowSearchDropdown(false);
    }
  };

  const handleSearchItemClick = async (student) => {
    setSelectedDept(student.department);
    setSelectedYear(student.year);
    setLevel('students');
    setSearchQuery('');
    setShowSearchDropdown(false);
    setHighlightedStudentId(student.id);

    // Fetch this folder's students
    await fetchFolderStudents(student.department, student.year);

    // Clear highlight after 3 seconds
    setTimeout(() => {
      setHighlightedStudentId(null);
    }, 4000);
  };

  // Excel Upload Submission
  const handleUploadExcelSubmit = async () => {
    if (!uploadFile) return;

    setUploading(true);
    try {
      const response = await studentsAPI.uploadExcel(uploadFile, uploadDept, uploadYear);
      toast.success(response.data.message);

      if (response.data.errors && response.data.errors.length > 0) {
        console.warn('Upload warnings/errors:', response.data.errors);
        toast.warning(`Uploaded with ${response.data.errors.length} warning(s)/error(s). Check browser console.`);
      }

      await fetchInitialData();
      if (level === 'students' && selectedDept && selectedYear) {
        fetchFolderStudents(selectedDept, selectedYear);
      }
      setShowUploadDialog(false);
      setUploadFile(null);
      setUploadStep(1);
    } catch (error) {
      const message = getErrorMessage(error, 'Upload failed');
      toast.error(message);
    } finally {
      setUploading(false);
    }
  };

  // Admin note
  const handleAddNote = async () => {
    if (!noteText.trim()) {
      toast.error('Please enter a note');
      return;
    }

    try {
      await studentsAPI.addNote(noteStudent.id, noteText);
      toast.success('Note added successfully');
      setShowNoteDialog(false);
      setNoteText('');
      // Reload lists
      fetchInitialData();
      if (selectedDept && selectedYear) {
        fetchFolderStudents(selectedDept, selectedYear);
      }
    } catch (error) {
      toast.error('Failed to add note');
    }
  };

  // Single Delete
  const handleDeleteStudent = async (studentId) => {
    if (!window.confirm('Are you sure you want to permanently delete this student?')) return;
    try {
      await studentsAPI.deleteStudent(studentId);
      toast.success('Student deleted');
      await fetchInitialData();
      if (selectedDept && selectedYear) {
        fetchFolderStudents(selectedDept, selectedYear);
      }
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to delete student');
      toast.error(message);
    }
  };

  // Bulk Move Trigger
  const handleOpenMoveDialog = (ids) => {
    setMoveTargetIds(ids);
    if (selectedDept) setMoveDept(selectedDept);
    if (selectedYear) setMoveYear(selectedYear);
    setShowMoveDialog(true);
  };

  // Move action execution (Single or Bulk)
  const handleExecuteMove = async () => {
    try {
      if (moveTargetIds.length === 1) {
        // Single move
        await studentsAPI.moveStudent(moveTargetIds[0], moveDept, moveYear);
      } else {
        // Bulk move
        await studentsAPI.bulkMove(moveTargetIds, moveDept, moveYear);
      }
      toast.success('Students moved successfully');
      setShowMoveDialog(false);
      setCheckedIds([]);

      // Refresh data
      await fetchInitialData();
      if (selectedDept && selectedYear) {
        // If the current folder's students moved, reload the folder
        fetchFolderStudents(selectedDept, selectedYear);
      }
    } catch (error) {
      toast.error('Failed to move student(s)');
    }
  };

  // Bulk Delete
  const handleExecuteBulkDelete = async () => {
    if (checkedIds.length === 0) return;
    if (!window.confirm(`Are you sure you want to permanently delete the ${checkedIds.length} selected student(s)?`)) return;

    try {
      await studentsAPI.bulkDelete(checkedIds);
      toast.success('Selected students deleted successfully');
      setCheckedIds([]);
      await fetchInitialData();
      if (selectedDept && selectedYear) {
        fetchFolderStudents(selectedDept, selectedYear);
      }
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to delete students');
      toast.error(message);
    }
  };

  // Edit student handler
  const handleOpenEdit = (student) => {
    setEditStudent(student);
    setEditFormData({
      roll_number: student.roll_number || '',
      full_name: student.full_name || '',
      department: student.department || '',
      year: student.year || '',
      dob: student.dob || '',
      email: student.email || '',
      phone_number: student.phone_number || ''
    });
    setShowEditDialog(true);
  };

  const handleUpdateStudent = async (e) => {
    e.preventDefault();
    const { roll_number, full_name, department, year, dob, email, phone_number } = editFormData;
    if (!roll_number || !full_name || !department || !year || !dob || !email || !phone_number) {
      toast.error('All fields are required');
      return;
    }
    setEditSaving(true);
    try {
      await studentsAPI.updateStudent(editStudent.id, editFormData);
      toast.success('Student updated successfully');
      setShowEditDialog(false);
      await fetchInitialData();
      if (selectedDept && selectedYear) {
        fetchFolderStudents(selectedDept, selectedYear);
      }
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to update student');
      toast.error(message);
    } finally {
      setEditSaving(false);
    }
  };

  // Rename folder handlers
  const handleOpenRenameFolder = (e, mode, dept, year) => {
    e.stopPropagation(); // prevent card navigation click
    setRenameMode(mode);
    setRenamingDept(dept);
    setRenamingYear(year || '');
    setRenameNewDept(dept);
    setRenameNewYear(year || '');
    setShowRenameDialog(true);
  };

  const handleRenameFolder = async () => {
    if (renameMode === 'dept' && !renameNewDept.trim()) {
      toast.error('Department name cannot be empty');
      return;
    }
    if (renameMode === 'year' && !renameNewYear.trim()) {
      toast.error('Year cannot be empty');
      return;
    }
    setRenameSaving(true);
    try {
      const resp = await studentsAPI.renameFolder(
        renamingDept,
        renameMode === 'dept' ? renameNewDept.trim() : renamingDept,
        renameMode === 'year' ? renamingYear : null,
        renameMode === 'year' ? renameNewYear.trim() : null
      );
      toast.success(resp.data.message);
      setShowRenameDialog(false);
      await fetchInitialData();
      // If we renamed the currently selected dept or year, update selection
      if (renameMode === 'dept') {
        if (selectedDept === renamingDept) setSelectedDept(renameNewDept.trim());
      } else {
        if (selectedYear === renamingYear) setSelectedYear(renameNewYear.trim());
      }
    } catch (error) {
      const message = getErrorMessage(error, 'Failed to rename folder');
      toast.error(message);
    } finally {
      setRenameSaving(false);
    }
  };

  // Selection state helpers
  const handleCheckAll = (e) => {
    if (e.target.checked) {
      setCheckedIds(students.map(s => s.id));
    } else {
      setCheckedIds([]);
    }
  };

  const handleCheckRow = (id) => {
    setCheckedIds(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6 animate-fade-in relative pb-20" data-testid="admin-students">
      {/* Top Header Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-6 h-6 text-indigo-600" />
            Student Directory
          </h1>
          <p className="text-slate-500">
            {allStudents.length} total students registered • {getDepartments().length} departments
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Global Search Autocomplete */}
          <div ref={searchContainerRef} className="relative w-64 sm:w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <Input
              placeholder="Search by name, roll, email..."
              value={searchQuery}
              onChange={handleSearchChange}
              className="pl-9 w-full shadow-sm border-slate-200 focus:border-indigo-500"
              data-testid="search-input"
            />
            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute z-50 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-xl max-h-72 overflow-y-auto divide-y divide-slate-100">
                {searchResults.map((student) => (
                  <button
                    key={student.id}
                    onClick={() => handleSearchItemClick(student)}
                    className="w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors flex flex-col justify-start"
                  >
                    <span className="font-medium text-slate-900 text-sm">{student.full_name}</span>
                    <div className="flex items-center gap-2 mt-0.5 text-xs text-slate-500">
                      <span className="font-mono bg-slate-100 px-1 py-0.5 rounded">{student.roll_number}</span>
                      <span>•</span>
                      <span className="font-semibold text-indigo-600">{student.department}</span>
                      <span>•</span>
                      <span>{formatYear(student.year)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
            {showSearchDropdown && searchResults.length === 0 && (
              <div className="absolute z-50 left-0 right-0 mt-1 bg-white border border-slate-200 rounded-lg shadow-xl p-4 text-center text-sm text-slate-500">
                No matching students found
              </div>
            )}
          </div>

          <Button 
            onClick={() => {
              setUploadDept(selectedDept || '');
              setUploadYear(selectedYear || '');
              setUploadFile(null);
              setUploadStep(1);
              setShowUploadDialog(true);
            }} 
            data-testid="upload-excel-btn"
            className="shadow-sm bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Excel
          </Button>
        </div>
      </div>

      {/* Breadcrumb & Navigation Bar */}
      <div className="flex items-center gap-2 bg-slate-50 border border-slate-200/60 p-3 rounded-lg text-sm text-slate-600 shadow-sm">
        <button 
          onClick={navigateToDepartments}
          className="hover:text-indigo-600 font-medium transition-colors"
        >
          Students
        </button>

        {selectedDept && (
          <>
            <ChevronRight className="w-4 h-4 text-slate-400" />
            <button 
              onClick={navigateToYears}
              className={`font-medium transition-colors ${!selectedYear ? 'text-indigo-600 font-semibold' : 'hover:text-indigo-600'}`}
            >
              {selectedDept}
            </button>
          </>
        )}

        {selectedYear && (
          <>
            <ChevronRight className="w-4 h-4 text-slate-400" />
            <span className="text-indigo-600 font-semibold">
              {formatYear(selectedYear)}
            </span>
          </>
        )}

        {/* Back Button */}
        {level !== 'departments' && (
          <button
            onClick={level === 'students' ? navigateToYears : navigateToDepartments}
            className="ml-auto flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 bg-white border border-slate-200/80 px-2.5 py-1 rounded transition-colors shadow-sm"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back
          </button>
        )}
      </div>

      {/* Main Content Area */}
      {loadingTree ? (
        <div className="flex justify-center py-16">
          <div className="spinner border-indigo-600" />
        </div>
      ) : (
        <>
          {/* LEVEL 1: DEPARTMENTS GRID */}
          {level === 'departments' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {getDepartments().length === 0 ? (
                <div className="col-span-full text-center py-16 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <FolderOpen className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                  <p className="text-slate-500 font-medium">No student records found</p>
                  <p className="text-sm text-slate-400 mt-1">Upload an Excel file with student directory to start</p>
                </div>
              ) : (
                getDepartments().map((dept) => (
                  <Card 
                    key={dept.name}
                    onClick={() => handleDeptClick(dept.name)}
                    className="card-hover cursor-pointer border-slate-200/80 hover:border-indigo-200/80 hover:shadow-md transition-all duration-200 group"
                  >
                    <CardContent className="p-6 flex items-center gap-4">
                      <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
                        <FolderOpen className="w-6 h-6 fill-indigo-100" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-outfit font-bold text-slate-900 text-lg">{dept.name}</h3>
                        <p className="text-sm text-slate-500">{dept.studentCount} Students</p>
                      </div>
                      <button
                        onClick={(e) => handleOpenRenameFolder(e, 'dept', dept.name, null)}
                        title="Rename Department"
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-indigo-100 text-indigo-500 hover:text-indigo-700 shrink-0"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <ChevronRight className="w-5 h-5 text-slate-300 shrink-0" />
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* LEVEL 2: ACADEMIC YEARS GRID */}
          {level === 'years' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {getYearsForDept(selectedDept).map((item) => (
                <Card
                  key={item.year}
                  onClick={() => handleYearClick(item.year)}
                  className="card-hover cursor-pointer border-slate-200/80 hover:border-indigo-200/80 hover:shadow-md transition-all duration-200 group"
                >
                  <CardContent className="p-6 flex items-center gap-4">
                    <div className="w-12 h-12 bg-slate-100 text-slate-600 rounded-xl flex items-center justify-center">
                      <Folder className="w-6 h-6 fill-slate-200" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-outfit font-bold text-slate-900 text-lg">{formatYear(item.year)}</h3>
                      <p className="text-sm text-slate-500">{item.count} Students</p>
                    </div>
                    <button
                      onClick={(e) => handleOpenRenameFolder(e, 'year', selectedDept, item.year)}
                      title="Rename Year"
                      className="opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg hover:bg-indigo-100 text-indigo-500 hover:text-indigo-700 shrink-0"
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <ChevronRight className="w-5 h-5 text-slate-300 shrink-0" />
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* LEVEL 3: STUDENTS LIST TABLE */}
          {level === 'students' && (
            <Card className="border-slate-200 shadow-sm overflow-hidden">
              <CardContent className="p-0">
                {loadingStudents ? (
                  <div className="flex justify-center py-16">
                    <div className="spinner border-indigo-600" />
                  </div>
                ) : students.length === 0 ? (
                  <div className="text-center py-16">
                    <FolderOpen className="w-12 h-12 mx-auto text-slate-300 mb-3" />
                    <p className="text-slate-500 font-medium">This folder is empty</p>
                    <button 
                      onClick={navigateToDepartments}
                      className="text-sm text-indigo-600 hover:text-indigo-700 font-medium mt-2 underline"
                    >
                      Return to Directory
                    </button>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader className="bg-slate-50/75 border-b border-slate-200">
                        <TableRow>
                          <TableHead className="w-12 text-center">
                            <input 
                              type="checkbox"
                              checked={checkedIds.length === students.length}
                              onChange={handleCheckAll}
                              className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
                            />
                          </TableHead>
                          <TableHead className="font-semibold text-slate-700">Roll Number</TableHead>
                          <TableHead className="font-semibold text-slate-700">Name</TableHead>
                          <TableHead className="font-semibold text-slate-700">Email</TableHead>
                          <TableHead className="font-semibold text-slate-700">Phone</TableHead>
                          <TableHead className="font-semibold text-slate-700">Notes</TableHead>
                          <TableHead className="font-semibold text-slate-700 text-right pr-6">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {students.map((student) => {
                          const isHighlighted = highlightedStudentId === student.id;
                          const isChecked = checkedIds.includes(student.id);
                          return (
                            <TableRow 
                              key={student.id} 
                              className={`transition-colors border-b border-slate-100 table-row-hover ${
                                isHighlighted ? 'bg-yellow-50 hover:bg-yellow-100/80 duration-500' : 
                                isChecked ? 'bg-slate-50/80' : ''
                              }`}
                              data-testid={`student-row-${student.id}`}
                            >
                              <TableCell className="text-center">
                                <input 
                                  type="checkbox"
                                  checked={isChecked}
                                  onChange={() => handleCheckRow(student.id)}
                                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4 cursor-pointer"
                                />
                              </TableCell>
                              <TableCell className="mono font-medium text-slate-900">{student.roll_number}</TableCell>
                              <TableCell className="font-medium text-slate-800">{student.full_name}</TableCell>
                              <TableCell className="text-slate-600 text-sm">{student.email}</TableCell>
                              <TableCell className="text-slate-600 text-sm mono">{student.phone_number}</TableCell>
                              <TableCell>
                                {student.admin_notes?.length > 0 && (
                                  <Badge variant="secondary" className="bg-slate-100 text-slate-700 hover:bg-slate-100">
                                    {student.admin_notes.length} note(s)
                                  </Badge>
                                )}
                              </TableCell>
                              <TableCell className="text-right pr-6">
                                <div className="flex gap-1 justify-end">
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => setSelectedStudent(student)}
                                    title="View Details"
                                    className="hover:bg-slate-100 text-slate-500 hover:text-slate-700"
                                    data-testid={`view-student-${student.id}`}
                                  >
                                    <Eye className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleOpenEdit(student)}
                                    title="Edit Student"
                                    className="hover:bg-indigo-50 text-slate-500 hover:text-indigo-600"
                                    data-testid={`edit-student-${student.id}`}
                                  >
                                    <Pencil className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => {
                                      setNoteStudent(student);
                                      setShowNoteDialog(true);
                                    }}
                                    title="Add Note"
                                    className="hover:bg-slate-100 text-slate-500 hover:text-slate-700"
                                    data-testid={`add-note-${student.id}`}
                                  >
                                    <StickyNote className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleOpenMoveDialog([student.id])}
                                    title="Move Student"
                                    className="hover:bg-slate-100 text-slate-500 hover:text-indigo-600"
                                  >
                                    <Move className="w-4 h-4" />
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleDeleteStudent(student.id)}
                                    title="Delete Student"
                                    className="hover:bg-red-50 text-red-500 hover:text-red-700"
                                    data-testid={`delete-student-${student.id}`}
                                  >
                                    <Trash2 className="w-4 h-4" />
                                  </Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* FLOATING BULK ACTION BAR */}
      {checkedIds.length > 0 && level === 'students' && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-slate-900/95 text-white shadow-2xl px-6 py-4 rounded-full flex items-center gap-6 border border-slate-800 backdrop-blur-md animate-fade-in-up z-50">
          <span className="text-sm font-medium text-slate-300">
            <strong className="text-white font-semibold">{checkedIds.length}</strong> student(s) selected
          </span>
          <div className="h-4 w-px bg-slate-800" />
          <div className="flex gap-2">
            <Button
              onClick={() => handleOpenMoveDialog(checkedIds)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full text-xs font-semibold px-4 py-2 flex items-center gap-1.5 shadow"
            >
              <Move className="w-3.5 h-3.5" />
              Move Selected
            </Button>
            <Button
              onClick={handleExecuteBulkDelete}
              className="bg-red-600 hover:bg-red-500 text-white rounded-full text-xs font-semibold px-4 py-2 flex items-center gap-1.5 shadow"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete Selected
            </Button>
          </div>
        </div>
      )}

      {/* MOVE STUDENT(S) DIALOG */}
      <Dialog open={showMoveDialog} onOpenChange={setShowMoveDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-outfit text-slate-950 font-bold">Move Student(s)</DialogTitle>
            <DialogDescription>
              Relocate {moveTargetIds.length} student(s) to a different Department and Academic Year.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Target Department</label>
              <select
                value={moveDept}
                onChange={(e) => setMoveDept(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
              >
                {DEPARTMENTS.map(d => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-semibold text-slate-700">Target Year</label>
              <select
                value={moveYear}
                onChange={(e) => setMoveYear(e.target.value)}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
              >
                {YEARS.map(y => (
                  <option key={y} value={y}>{formatYear(y)}</option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMoveDialog(false)} className="rounded-lg">
              Cancel
            </Button>
            <Button onClick={handleExecuteMove} className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg">
              Confirm Move
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Excel Upload Dialog - Multi-Step Wizard */}
      <Dialog 
        open={showUploadDialog} 
        onOpenChange={(open) => {
          if (!open) { setUploadFile(null); setUploadStep(1); }
          setShowUploadDialog(open);
        }}
      >
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-outfit text-slate-950 font-bold">Upload Student Data</DialogTitle>
            <DialogDescription>
              Follow the steps below to upload student records from an Excel file.
            </DialogDescription>
          </DialogHeader>

          {/* Step Indicator */}
          <div className="flex items-center justify-between px-2 pt-2 pb-1">
            {[{n:1, label:'Select Target'}, {n:2, label:'Choose File'}, {n:3, label:'Review & Upload'}].map((s, idx) => (
              <div key={s.n} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1 flex-shrink-0">
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold transition-all duration-300 ${
                    uploadStep > s.n 
                      ? 'bg-emerald-500 text-white shadow-sm' 
                      : uploadStep === s.n 
                        ? 'bg-indigo-600 text-white shadow-md ring-4 ring-indigo-100' 
                        : 'bg-slate-100 text-slate-400 border border-slate-200'
                  }`}>
                    {uploadStep > s.n ? <CheckCircle2 className="w-5 h-5" /> : s.n}
                  </div>
                  <span className={`text-[11px] font-semibold whitespace-nowrap transition-colors ${
                    uploadStep >= s.n ? 'text-slate-700' : 'text-slate-400'
                  }`}>{s.label}</span>
                </div>
                {idx < 2 && (
                  <div className={`flex-1 h-0.5 mx-2 mt-[-18px] rounded-full transition-colors duration-300 ${
                    uploadStep > s.n ? 'bg-emerald-400' : 'bg-slate-200'
                  }`} />
                )}
              </div>
            ))}
          </div>

          <div className="space-y-4 py-3 min-h-[200px]">

            {/* STEP 1: Department & Year Selection */}
            {uploadStep === 1 && (
              <div className="animate-fade-in space-y-4">
                <div className="bg-indigo-50/50 border border-indigo-100 rounded-xl p-4">
                  <p className="text-sm text-indigo-800 font-medium mb-1">📋 Where should these students be placed?</p>
                  <p className="text-xs text-indigo-600/80">Choose a department and year, or leave as "Read from Excel" to use values from the spreadsheet columns.</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-semibold text-slate-700">Target Department</label>
                    <select
                      value={uploadDept}
                      onChange={(e) => setUploadDept(e.target.value)}
                      className="w-full px-3 py-2.5 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
                    >
                      <option value="">Read from Excel sheet</option>
                      {DEPARTMENTS.map(d => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-semibold text-slate-700">Target Year</label>
                    <select
                      value={uploadYear}
                      onChange={(e) => setUploadYear(e.target.value)}
                      className="w-full px-3 py-2.5 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
                    >
                      <option value="">Read from Excel sheet</option>
                      {YEARS.map(y => (
                        <option key={y} value={y}>{formatYear(y)}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* STEP 2: File Upload */}
            {uploadStep === 2 && (
              <div className="animate-fade-in space-y-4">
                <div className="bg-amber-50/50 border border-amber-100 rounded-xl p-4">
                  <p className="text-sm text-amber-800 font-medium mb-1">📁 Select your Excel file</p>
                  <p className="text-xs text-amber-700/80">The file must contain columns: <strong>Roll Number, Full Name, DOB, Email, Phone Number</strong>{!uploadDept && ', Department'}{!uploadYear && ', Year'}.</p>
                </div>
                <div className="space-y-1.5">
                  {uploadFile ? (
                    <div className="flex items-center justify-between border border-emerald-200 bg-emerald-50/40 rounded-xl p-4 text-sm text-slate-700">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-lg flex items-center justify-center">
                          <FileSpreadsheet className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="font-semibold text-emerald-700 truncate max-w-[260px]">{uploadFile.name}</p>
                          <p className="text-xs text-slate-400">{(uploadFile.size / 1024).toFixed(1)} KB</p>
                        </div>
                      </div>
                      <button 
                        type="button"
                        onClick={() => setUploadFile(null)} 
                        className="text-xs text-red-500 hover:text-red-700 font-semibold underline"
                      >
                        Remove
                      </button>
                    </div>
                  ) : (
                    <label className="block">
                      <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-200 hover:border-indigo-400 rounded-xl p-10 cursor-pointer transition-all hover:bg-indigo-50/30">
                        <FileSpreadsheet className="w-14 h-14 text-slate-300 mb-3" />
                        <p className="text-sm text-slate-600 font-medium mb-1">Click to select Excel file</p>
                        <p className="text-xs text-slate-400">.xlsx or .xls files supported</p>
                      </div>
                      <input
                        type="file"
                        accept=".xlsx,.xls"
                        onChange={(e) => {
                          const file = e.target.files[0];
                          if (file) {
                            if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
                              toast.error('Please select an Excel file (.xlsx or .xls)');
                            } else {
                              setUploadFile(file);
                            }
                          }
                        }}
                        className="hidden"
                        disabled={uploading}
                        data-testid="excel-file-input"
                      />
                    </label>
                  )}
                </div>
              </div>
            )}

            {/* STEP 3: Review & Upload */}
            {uploadStep === 3 && (
              <div className="animate-fade-in space-y-4">
                <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-4">
                  <p className="text-sm text-emerald-800 font-medium mb-1">✅ Review your upload settings</p>
                  <p className="text-xs text-emerald-700/80">Verify the information below, then click Upload to process the records.</p>
                </div>
                <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-sm text-slate-500 font-medium">Department</span>
                    <span className="text-sm font-bold text-slate-800">{uploadDept || '📄 From Excel Sheet'}</span>
                  </div>
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-sm text-slate-500 font-medium">Year</span>
                    <span className="text-sm font-bold text-slate-800">{uploadYear ? formatYear(uploadYear) : '📄 From Excel Sheet'}</span>
                  </div>
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-sm text-slate-500 font-medium">File</span>
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4 text-emerald-500" />
                      <span className="text-sm font-bold text-slate-800 truncate max-w-[200px]">{uploadFile?.name}</span>
                    </div>
                  </div>
                  <div className="flex items-center justify-between px-4 py-3">
                    <span className="text-sm text-slate-500 font-medium">File Size</span>
                    <span className="text-sm font-semibold text-slate-600">{uploadFile ? (uploadFile.size / 1024).toFixed(1) + ' KB' : '—'}</span>
                  </div>
                  <div className="flex items-center justify-between px-4 py-3 bg-amber-50/40">
                    <span className="text-sm text-amber-700 font-medium">Duplicate Handling</span>
                    <span className="text-xs font-semibold text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">Duplicates will be skipped</span>
                  </div>
                </div>

                {uploading && (
                  <div className="flex items-center justify-center pt-2">
                    <div className="spinner border-indigo-600 mr-2" />
                    <span className="text-sm text-slate-500 font-medium">Processing records...</span>
                  </div>
                )}
              </div>
            )}

          </div>

          {/* Wizard Footer Navigation */}
          <DialogFooter className="flex !justify-between gap-2 pt-2 border-t border-slate-100">
            <div>
              {uploadStep > 1 && !uploading && (
                <Button 
                  variant="outline" 
                  onClick={() => setUploadStep(prev => prev - 1)}
                  className="rounded-lg"
                >
                  <ArrowLeft className="w-4 h-4 mr-1.5" />
                  Back
                </Button>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button 
                variant="outline" 
                onClick={() => {
                  setShowUploadDialog(false);
                  setUploadFile(null);
                  setUploadStep(1);
                }} 
                disabled={uploading}
                className="rounded-lg"
              >
                Cancel
              </Button>

              {uploadStep < 3 && (
                <Button 
                  onClick={() => setUploadStep(prev => prev + 1)}
                  disabled={uploadStep === 2 && !uploadFile}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm"
                >
                  Proceed
                  <ArrowRight className="w-4 h-4 ml-1.5" />
                </Button>
              )}

              {uploadStep === 3 && (
                <Button 
                  onClick={handleUploadExcelSubmit} 
                  disabled={!uploadFile || uploading}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm"
                >
                  <Upload className="w-4 h-4 mr-1.5" />
                  Upload
                </Button>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Student Detail Dialog */}
      <Dialog open={!!selectedStudent} onOpenChange={() => setSelectedStudent(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-outfit text-slate-950 font-bold">Student Details</DialogTitle>
          </DialogHeader>
          {selectedStudent && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-slate-500 font-medium">Roll Number</p>
                  <p className="font-mono font-semibold text-slate-800">{selectedStudent.roll_number}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">Full Name</p>
                  <p className="font-semibold text-slate-800">{selectedStudent.full_name}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">Department</p>
                  <p className="font-semibold text-indigo-600">{selectedStudent.department}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">Year</p>
                  <p className="font-semibold text-slate-800">{formatYear(selectedStudent.year)}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">DOB</p>
                  <p className="mono font-semibold text-slate-800">{selectedStudent.dob}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">Email</p>
                  <p className="text-sm font-semibold text-slate-800">{selectedStudent.email}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">Phone</p>
                  <p className="mono font-semibold text-slate-800">{selectedStudent.phone_number}</p>
                </div>
              </div>

              {selectedStudent.admin_notes?.length > 0 && (
                <div className="pt-4 border-t border-slate-100">
                  <p className="text-sm font-bold text-slate-900 mb-2">Admin Notes</p>
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {selectedStudent.admin_notes.map((note, idx) => (
                      <div key={idx} className="bg-slate-50 border border-slate-150 p-3 rounded-lg text-sm">
                        <p className="text-slate-700">{note.note}</p>
                        <p className="text-xs text-slate-400 mt-1 font-medium">
                          {new Date(note.added_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Add Note Dialog */}
      <Dialog open={showNoteDialog} onOpenChange={setShowNoteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-outfit text-slate-950 font-bold">Add Admin Note</DialogTitle>
            <DialogDescription>
              Add a note for {noteStudent?.full_name} ({noteStudent?.roll_number})
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Textarea
              placeholder="Enter student note..."
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              rows={4}
              className="border-slate-200 rounded-lg focus:ring-indigo-500"
              data-testid="note-input"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowNoteDialog(false)} className="rounded-lg">
              Cancel
            </Button>
            <Button onClick={handleAddNote} className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg" data-testid="save-note-btn">
              Save Note
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Student Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-outfit text-slate-950 font-bold">Edit Student Details</DialogTitle>
            <DialogDescription>
              Update information for {editStudent?.full_name} ({editStudent?.roll_number})
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateStudent} className="space-y-4 py-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Roll Number</label>
                <Input
                  value={editFormData.roll_number}
                  onChange={(e) => setEditFormData({ ...editFormData, roll_number: e.target.value })}
                  className="border-slate-200 rounded-lg focus:ring-indigo-500"
                  data-testid="edit-student-roll"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Full Name</label>
                <Input
                  value={editFormData.full_name}
                  onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                  className="border-slate-200 rounded-lg focus:ring-indigo-500"
                  data-testid="edit-student-name"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Department</label>
                <select
                  value={editFormData.department}
                  onChange={(e) => setEditFormData({ ...editFormData, department: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
                  data-testid="edit-student-dept"
                >
                  {DEPARTMENTS.map(d => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Year</label>
                <select
                  value={editFormData.year}
                  onChange={(e) => setEditFormData({ ...editFormData, year: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
                  data-testid="edit-student-year"
                >
                  {YEARS.map(y => (
                    <option key={y} value={y}>{formatYear(y)}</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">DOB (DD-MM-YYYY)</label>
                <Input
                  value={editFormData.dob}
                  onChange={(e) => setEditFormData({ ...editFormData, dob: e.target.value })}
                  placeholder="DD-MM-YYYY"
                  className="border-slate-200 rounded-lg focus:ring-indigo-500"
                  data-testid="edit-student-dob"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">Email</label>
                <Input
                  type="email"
                  value={editFormData.email}
                  onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                  className="border-slate-200 rounded-lg focus:ring-indigo-500"
                  data-testid="edit-student-email"
                />
              </div>
              <div className="space-y-1.5 col-span-2">
                <label className="text-sm font-semibold text-slate-700">Phone Number</label>
                <Input
                  value={editFormData.phone_number}
                  onChange={(e) => setEditFormData({ ...editFormData, phone_number: e.target.value })}
                  className="border-slate-200 rounded-lg focus:ring-indigo-500"
                  data-testid="edit-student-phone"
                />
              </div>
            </div>
            <DialogFooter className="pt-4 border-t border-slate-100">
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowEditDialog(false)}
                disabled={editSaving}
                className="rounded-lg"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={editSaving}
                className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm"
                data-testid="save-edit-btn"
              >
                {editSaving ? (
                  <><div className="spinner w-3.5 h-3.5 mr-2 border-white" /> Saving...</>
                ) : (
                  'Save Changes'
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Rename Folder Dialog */}
      <Dialog open={showRenameDialog} onOpenChange={setShowRenameDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-outfit text-slate-950 font-bold">
              {renameMode === 'dept' ? '✏️ Rename Department' : '✏️ Rename Year'}
            </DialogTitle>
            <DialogDescription>
              {renameMode === 'dept'
                ? `Rename department "${renamingDept}" — updates all students inside.`
                : `Rename year "${formatYear(renamingYear)}" in ${renamingDept} — updates all students inside.`
              }
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 space-y-4">
            {renameMode === 'dept' ? (
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">New Department Name</label>
                <Input
                  value={renameNewDept}
                  onChange={(e) => setRenameNewDept(e.target.value)}
                  placeholder="e.g. CSE"
                  className="border-slate-200 rounded-lg focus:ring-indigo-500"
                  autoFocus
                />
              </div>
            ) : (
              <div className="space-y-1.5">
                <label className="text-sm font-semibold text-slate-700">New Year Value</label>
                <select
                  value={renameNewYear}
                  onChange={(e) => setRenameNewYear(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm font-medium text-slate-800"
                >
                  {YEARS.map(y => (
                    <option key={y} value={y}>{formatYear(y)}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="flex items-start gap-2 bg-amber-50 border border-amber-100 rounded-lg p-3 text-xs text-amber-700">
              <span>⚠️</span>
              <span>All students in this folder will be updated to reflect the new name.</span>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowRenameDialog(false)}
              disabled={renameSaving}
              className="rounded-lg"
            >
              Cancel
            </Button>
            <Button
              onClick={handleRenameFolder}
              disabled={renameSaving}
              className="bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm"
            >
              {renameSaving ? (
                <><div className="spinner w-3.5 h-3.5 mr-2 border-white" /> Saving...</>
              ) : 'Rename Folder'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminStudentFolders;
