#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <stdio.h>
int main(void) {
    PFNEGLGETPLATFORMDISPLAYEXTPROC get_display =
        (void *)eglGetProcAddress("eglGetPlatformDisplayEXT");
    EGLDisplay d = get_display(EGL_PLATFORM_SURFACELESS_MESA, EGL_DEFAULT_DISPLAY, NULL);
    EGLint major, minor;
    if (!eglInitialize(d, &major, &minor)) {
        fprintf(stderr, "eglInitialize: 0x%x\n", eglGetError());
        return 1;
    }
    EGLint attributes[] = {EGL_SURFACE_TYPE,
                           EGL_PBUFFER_BIT,
                           EGL_RENDERABLE_TYPE,
                           EGL_OPENGL_ES2_BIT,
                           EGL_RED_SIZE,
                           8,
                           EGL_GREEN_SIZE,
                           8,
                           EGL_BLUE_SIZE,
                           8,
                           EGL_NONE};
    EGLConfig config;
    EGLint count;
    if (!eglChooseConfig(d, attributes, &config, 1, &count) || !count)
        return 2;
    EGLint size[] = {EGL_WIDTH, 16, EGL_HEIGHT, 16, EGL_NONE};
    EGLSurface surface = eglCreatePbufferSurface(d, config, size);
    EGLint version[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
    eglBindAPI(EGL_OPENGL_ES_API);
    EGLContext context = eglCreateContext(d, config, EGL_NO_CONTEXT, version);
    if (!eglMakeCurrent(d, surface, surface, context)) {
        fprintf(stderr, "eglMakeCurrent: 0x%x\n", eglGetError());
        return 3;
    }
    printf("EGL %d.%d; GL %s; renderer %s\n", major, minor, glGetString(GL_VERSION),
           glGetString(GL_RENDERER));
    glViewport(0, 0, 16, 16);
    glClearColor(0.25f, 0.5f, 0.75f, 1);
    glClear(GL_COLOR_BUFFER_BIT);
    glFinish();
    unsigned char pixel[4] = {0};
    glReadPixels(8, 8, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
    printf("Pixel: %u %u %u %u; error 0x%x\n", pixel[0], pixel[1], pixel[2], pixel[3],
           glGetError());
    if (!(pixel[0] >= 63 && pixel[0] <= 65 && pixel[1] >= 127 && pixel[1] <= 129 &&
          pixel[2] >= 190 && pixel[2] <= 192))
        return 4;
    const char *vs = "attribute vec2 position; void main(){gl_Position=vec4(position,0.0,1.0);}";
    const char *fs = "precision mediump float; void main(){gl_FragColor=vec4(0.75,0.25,0.5,1.0);}";
    GLuint vertex = glCreateShader(GL_VERTEX_SHADER), fragment = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(vertex, 1, &vs, 0);
    glCompileShader(vertex);
    glShaderSource(fragment, 1, &fs, 0);
    glCompileShader(fragment);
    GLuint program = glCreateProgram();
    glAttachShader(program, vertex);
    glAttachShader(program, fragment);
    glBindAttribLocation(program, 0, "position");
    glLinkProgram(program);
    GLint linked = 0;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) {
        char log[1024];
        glGetProgramInfoLog(program, sizeof(log), 0, log);
        puts(log);
        return 5;
    }
    glUseProgram(program);
    float vertices[] = {-1, -1, 1, -1, 0, 1};
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, vertices);
    glEnableVertexAttribArray(0);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glFinish();
    glReadPixels(8, 8, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
    printf("Triangle: %u %u %u %u; error 0x%x\n", pixel[0], pixel[1], pixel[2], pixel[3],
           glGetError());
    return !(pixel[0] >= 190 && pixel[0] <= 192 && pixel[1] >= 63 && pixel[1] <= 65 &&
             pixel[2] >= 127 && pixel[2] <= 129);
}
