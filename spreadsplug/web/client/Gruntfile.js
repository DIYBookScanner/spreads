module.exports = function(grunt) {

  var dejsx = require('grunt-react').browserify;

  grunt.loadNpmTasks('grunt-sass');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-browserify');
  grunt.loadNpmTasks('grunt-react');
  grunt.loadNpmTasks('grunt-contrib-uglify');

  grunt.initConfig({
    pkg: grunt.file.readJSON('package.json'),

    browserify: {
      options: {
        transform: [dejsx],
        debug: true
      },
      app: {
        src: 'src/main.js',
        dest: 'spreads.js'
      }
    },
    uglify: {
      spreads: {
        options: {
          sourceMap: './spreads.min-map.js',
          sourceMapIn: './spreads.js'
        },
        files: {
            './spreads.min.js': ['./spreads.js']
        }
      }
    },
    watch: {
      grunt: { files: ['Gruntfile.js'] },
      src: {
        files: ['src/**/*.js'],
        tasks: ['browserify']
      },
      sass: {
        files: 'scss/**/*.scss',
        tasks: ['sass']
      }
    },
    sass: {
      dist: {
        options: {
          outputStyle: 'compressed'
        },
        files: {
          'spreads.css': 'scss/app.scss'
        }
      }
    }
  });

  grunt.registerTask('build', ['sass']);
  grunt.registerTask('default', ['build', 'browserify', 'uglify']);
};