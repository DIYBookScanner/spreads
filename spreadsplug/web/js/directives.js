/* globals angular */

angular.module('spreads').directive('spreadsConfig', function($http, $compile, $interpolate, $q) {
    function _buildFormGroup(name, option) {
        return $interpolate(
            '<div class="form-group">'+
            '  <label for="cfg-' + name + '">' +
            option.docstring +
            '  </label>' +
            '  {{input}}' +
            '</div>'
        );
    }

    function buildSelect(section, name, option) {
        var markup = _buildFormGroup(name, option);
        var select = '<select id="cfg-' + name + '"'+
                        '        class="form-control"' +
                        '        ng-model="configuration.' + section + '.' + name + '">';
        option.value.forEach(function(each) {
            select += '<option>' + each + '</option>';
        });
        select += '</select>';
        return markup({input: select});
    }

    function buildInput(section, name, option) {
        var markup = _buildFormGroup(name, option);
        var type = 'text';
        if (typeof(option.value) === 'number') {
            type = 'number';
        }
        return markup(
            {input: '<input type="' + type + '" class="form-control"' +
                    '       id=cfg-' + name + '"' +
                    '       placeholder="' + option.value + '"' +
                    '       ng-model="configuration.' + section + '.' + name + '">'
            }
        );
    }

    function buildCheckbox(section, name, option) {
        return '<div class="checkbox">' +
                '  <label>' +
                '    <input type="checkbox" id="cfg-' + name + '"' +
                    '      ng-model="configuration.' + section + '.' + name + '">' +
                    option.docstring +
                '  </label>' +
                '</div>';
    }

    function buildTab(section, active) {
        var markup = '';
        if (active) {
            markup += '<li class="active">';
        } else {
            markup += '<li>';
        }
        markup += '<a href="#tab-' + section + '" data-toggle="tab">' +
                    section.charAt(0).toUpperCase() + section.slice(1) +
                    '</a>';
        markup += '</li>';
        return markup;
    }

    function buildTabContainer(section, template, active) {
        if (active) {
            active = 'active';
        }
        var markup = $interpolate(
            '<div class="tab-pane ' + active + '" id="tab-{{section}}">' +
            '  {{form}}' +
            '</div>'
        );
        var formComponents = [];
        for (var key in template) {
            if (template.hasOwnProperty(key)) {
                var option = template[key];
                if (typeof(option.value) === 'boolean') {
                    formComponents.push(buildCheckbox(section, key, option));
                } else if (typeof(option.value) === 'object' && option.selectable) {
                    formComponents.push(buildSelect(section, key, option));
                } else if (typeof(option.value) === 'object') {
                    // TODO: Find a way to make this user-friendly
                    formComponents.push('');
                } else {
                    formComponents.push(buildInput(section, key, option));
                }
            }
        }
        var form = formComponents.join('\n');
        return markup({section: section, form: form});
    }

    function buildForm(template) {
        var markup = $interpolate(
            '<form role="form" ng-controller="ConfigCtrl">' +
            '  <ul class="nav nav-tabs" id="configTab">' +
            '  {{tabs}}' +
            '  </ul>' +
            '  <div class="tab-content">' +
            '  {{tabcontents}}' +
            '  </div>' +
            '</form>');
        var tabs = [];
        var tabContents = [];
        var active = true;
        for (var section in template) {
            if (template.hasOwnProperty(section)) {
                tabs.push(buildTab(section, active));
                tabContents.push(buildTabContainer(section, template[section], active));
                active = false;
            }
        }
        return markup({tabs: tabs.join('\n'),
                        tabcontents: tabContents.join('\n')});
    }

    var directiveData, dataPromise;
    function loadTemplate() {
        if (dataPromise) {
            return dataPromise;
        }
        var deferred = $q.defer();
        dataPromise = deferred.promise;
        if (directiveData) {
            deferred.resolve(directiveData);
        } else {
            console.debug('Downloading template');
            $http.get('api/configuration/template')
            .success(function(data) {
                directiveData = data;
                deferred.resolve(directiveData);
            });
        }
        return dataPromise;
    }

    return {
        restrict: 'E',
        controller: 'ConfigCtrl',
        compile: function() {
            loadTemplate();
            return function(scope, element) {
                loadTemplate().then(function(data) {
                    console.debug('Inserting template markup');
                    var markup = $compile(buildForm(data))(scope);
                    element.replaceWith(markup);
                });
            };
        }
    };
});
