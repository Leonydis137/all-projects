/* UUMA native hot path. Author & builder: Juan-louw Greyling <juanlouw.greyling@gmail.com>
 * mix_buffer(buf: bytearray, state: bytes, i: int) -> None
 * Bit-exact port of: buf[j] = (state[j % len(state)] + i + j) & 0xFF  */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
static PyObject *mix_buffer(PyObject *self, PyObject *args) {
    Py_buffer buf, st; long i;
    if (!PyArg_ParseTuple(args, "w*y*l", &buf, &st, &i)) return NULL;
    if (st.len == 0) { PyBuffer_Release(&buf); PyBuffer_Release(&st);
        PyErr_SetString(PyExc_ValueError, "state must be non-empty"); return NULL; }
    unsigned char *b = (unsigned char *)buf.buf; const unsigned char *s = (const unsigned char *)st.buf;
    Py_ssize_t n = buf.len, m = st.len, k = 0;
    for (Py_ssize_t j = 0; j < n; j++) { b[j] = (unsigned char)(s[k] + i + j); if (++k == m) k = 0; }
    PyBuffer_Release(&buf); PyBuffer_Release(&st); Py_RETURN_NONE;
}
static PyMethodDef M[] = {{"mix_buffer", mix_buffer, METH_VARARGS, "Fill buffer (bit-exact with the pure-Python loop)."},{NULL,NULL,0,NULL}};
static struct PyModuleDef D = {PyModuleDef_HEAD_INIT, "uuma_native", NULL, -1, M};
PyMODINIT_FUNC PyInit_uuma_native(void) { return PyModule_Create(&D); }
