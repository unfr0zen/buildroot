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
    if (!(pixel[0] >= 190 && pixel[0] <= 192 && pixel[1] >= 63 && pixel[1] <= 65 &&
          pixel[2] >= 127 && pixel[2] <= 129)) return 6;
    vs = "attribute vec2 position; attribute vec2 uv; varying vec2 texcoord;"
         "void main(){gl_Position=vec4(position,0.0,1.0);texcoord=uv;}";
    fs = "precision mediump float; varying vec2 texcoord; uniform sampler2D image;"
         "void main(){gl_FragColor=texture2D(image,texcoord);}";
    glShaderSource(vertex, 1, &vs, NULL);
    glCompileShader(vertex);
    glShaderSource(fragment, 1, &fs, NULL);
    glCompileShader(fragment);
    glBindAttribLocation(program, 1, "uv");
    glLinkProgram(program);
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) return 7;
    glUseProgram(program);
    float quad[] = {-1, -1, 1, -1, -1, 1, 1, 1};
    float uv[] = {0, 0, 1, 0, 0, 1, 1, 1};
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, quad);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 0, uv);
    glEnableVertexAttribArray(1);
    unsigned char colors[] = {255, 0, 0, 255, 0, 255, 0, 255,
                              0, 0, 255, 255, 255, 255, 0, 255};
    GLuint texture;
    glGenTextures(1, &texture);
    glBindTexture(GL_TEXTURE_2D, texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 2, 2, 0, GL_RGBA,
                 GL_UNSIGNED_BYTE, colors);
    glUniform1i(glGetUniformLocation(program, "image"), 0);
    glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
    glFinish();
    unsigned failures = 0;
    for (unsigned i = 0; i < 4; i++) {
        glReadPixels(i % 2 ? 12 : 4, i / 2 ? 12 : 4, 1, 1,
                     GL_RGBA, GL_UNSIGNED_BYTE, pixel);
        printf("Texture %u: %u %u %u %u; error 0x%x\n", i,
               pixel[0], pixel[1], pixel[2], pixel[3], glGetError());
        for (unsigned j = 0; j < 4; j++) {
            if (pixel[j] != colors[i * 4 + j]) failures++;
        }
    }
    if (failures) return 8;
    fs = "precision mediump float; varying vec2 texcoord; uniform sampler2D image;"
         "uniform float selectColor; void main(){if(selectColor>0.5)"
         "gl_FragColor=vec4(1.0,0.0,1.0,1.0);"
         "else gl_FragColor=texture2D(image,texcoord);}";
    glShaderSource(fragment, 1, &fs, NULL);
    glCompileShader(fragment);
    glLinkProgram(program);
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) return 9;
    glUseProgram(program);
    for (unsigned selected = 0; selected < 2; selected++) {
        glUniform1f(glGetUniformLocation(program, "selectColor"), selected);
        glDrawArrays(GL_TRIANGLE_STRIP, 0, 4);
        glFinish();
        glReadPixels(4, 4, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, pixel);
        printf("Branch %u: %u %u %u %u; error 0x%x\n", selected,
               pixel[0], pixel[1], pixel[2], pixel[3], glGetError());
        if (pixel[0] != 255 || pixel[1] || pixel[2] != selected * 255 ||
            pixel[3] != 255) return 10;
    }
    return 0;
}
